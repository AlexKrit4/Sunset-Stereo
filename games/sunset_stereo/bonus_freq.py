"""Lock natural 3-scatter / 4-scatter frequencies on base and ante.

Book counts already match 1/200, 1/1000 (base) and 1/100, 1/500 (ante).
Stake samples by LUT weight, so those rates only hold after this reweight.
High-paying bonus books stay in the pack at min weight; probability mass
sits on cheaper bonus books, and leftover mass goes to empty (zero) books
so RTP stays ~95%.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import subprocess
import threading
import zipfile
from typing import Iterable

from weight_modes import (
    MODE_COST,
    RTP_TOL,
    TARGET_RTP,
    _gcd_many,
    lut_stats,
    write_lut,
)
from base_feature import FEATURE_RATE, WILD_COUNT_BANDS, classify_feature

FEATURE_CLASSES = (
    "feature_sync",
    "feature_w1",
    "feature_w2",
    "feature_w3",
    "feature_w4",
)

FEATURE_SHARE = {"feature_sync": 0.5}
_acc = 0
for _share, _count in WILD_COUNT_BANDS:
    FEATURE_SHARE[f"feature_w{_count}"] = 0.5 * (_share / 100.0)
    _acc += _share
assert abs(_acc - 100) < 1e-9
assert abs(sum(FEATURE_SHARE.values()) - 1.0) < 1e-9

BONUS_FREQ = {
    "base": {"fg3": 1.0 / 200.0, "fg4": 1.0 / 1000.0},
    "scatter": {"fg3": 1.0 / 100.0, "fg4": 1.0 / 500.0},
}

SCALE = 1_000_000_000
HIT_RATE_FLOOR = 1.0 / 50.0


def classify_events(events: list, cents: int) -> str:
    trigger = next((event for event in events or [] if event.get("type") == "freeSpinTrigger"), None)
    if trigger is not None:
        n_scatter = len(trigger.get("positions") or [])
        return "fg4" if n_scatter >= 4 else "fg3"
    types = [event.get("type") for event in events or []]
    if "updateFreeSpin" in types:
        return "fg4" if "placeWild" in types else "fg3"
    if int(cents) <= 0:
        return "zero"
    return "hit"


def classify_book(book: dict) -> str:
    criteria = str(book.get("criteria") or "")
    cents = int(book.get("payoutMultiplier") or 0)
    # Base/ante wincap books are 4-scatter wild bonuses (game_config quotas).
    if criteria == "freegame":
        return "fg3"
    if criteria in {"freegame4", "wincap"}:
        return "fg4"
    feature = classify_feature(book)
    if feature:
        return feature
    if criteria == "0":
        return "zero"
    if criteria == "basegame":
        return "hit" if cents > 0 else "zero"
    return classify_events(book.get("events") or [], cents)


def _cheap_raw(cents: int, tilt: float) -> float:
    return max(int(cents) / 100.0, 0.1) ** tilt


def _mu(items: list[tuple[int, int]], tilt: float) -> float:
    num = 0.0
    den = 0.0
    for _book_id, cents in items:
        raw = _cheap_raw(cents, tilt)
        num += raw * (cents / 100.0)
        den += raw
    return num / den if den else 0.0


def _mass_weights(items: list[tuple[int, int]], mass: float, tilt: float) -> dict[int, int]:
    raw = [_cheap_raw(cents, tilt) for _book_id, cents in items]
    total = sum(raw) or 1.0
    out: dict[int, int] = {}
    for (book_id, _cents), value in zip(items, raw):
        out[int(book_id)] = max(1, int(round(mass * (value / total) * SCALE)))
    return out


def _even_weights(items: list[tuple[int, int]], mass: float) -> dict[int, int]:
    if not items:
        return {}
    each = max(1, int(round((mass / len(items)) * SCALE)))
    return {int(book_id): each for book_id, _cents in items}


def assign_bonus_freq_weights(
    rows: list[tuple[int, int, int]],
    mode: str,
    classes: dict[int, str],
) -> list[tuple[int, int, int]]:
    """Pin 3-scatter / 4-scatter rates, then restore RTP with zeros and hits."""
    freq = BONUS_FREQ[mode]
    cost = MODE_COST[mode]
    p3 = float(freq["fg3"])
    p4 = float(freq["fg4"])
    present_feat = {kind for kind in classes.values() if kind in FEATURE_SHARE}
    p_feat = FEATURE_RATE if present_feat else 0.0
    by_class: dict[str, list[tuple[int, int]]] = {
        "fg3": [],
        "fg4": [],
        "feature_sync": [],
        "feature_w1": [],
        "feature_w2": [],
        "feature_w3": [],
        "feature_w4": [],
        "hit": [],
        "zero": [],
    }
    payouts = {}
    for book_id, _weight, cents in rows:
        kind = classes.get(int(book_id), "hit" if cents > 0 else "zero")
        if kind not in by_class:
            kind = "hit" if cents > 0 else "zero"
        by_class[kind].append((int(book_id), int(cents)))
        payouts[int(book_id)] = int(cents)
    if not by_class["fg3"] or not by_class["fg4"] or not by_class["zero"]:
        raise ValueError(f"{mode} needs fg3, fg4, and zero books to lock bonus frequency")
    feat_groups = {kind: items for kind, items in by_class.items() if kind in FEATURE_SHARE and items}
    if p_feat and not feat_groups:
        p_feat = 0.0
    feat_mass = {
        kind: p_feat * FEATURE_SHARE[kind]
        for kind in feat_groups
    }
    if feat_mass:
        scale = p_feat / sum(feat_mass.values())
        feat_mass = {kind: mass * scale for kind, mass in feat_mass.items()}

    bonus_tilt = -6.0
    lo, hi = -12.0, 0.0
    for _ in range(28):
        mid = (lo + hi) / 2.0
        bonus_ev = p3 * _mu(by_class["fg3"], mid) + p4 * _mu(by_class["fg4"], mid)
        # Leave room for a 1/50 hit-rate of cheap base hits.
        if bonus_ev > TARGET_RTP * cost * 0.82:
            hi = mid
        else:
            lo = mid
        bonus_tilt = hi
    bonus_ev = p3 * _mu(by_class["fg3"], bonus_tilt) + p4 * _mu(by_class["fg4"], bonus_tilt)
    feat_tilt = -8.0
    feat_ev = 0.0
    if feat_groups and p_feat > 0:
        # Feature books do not have to pay. Cheap/zero outcomes carry each
        # subtype's locked share so 50/50 and 80/15/4/1 survive the RTP fit.
        feat_cap = max(0.0, TARGET_RTP * cost - bonus_ev - 0.08 * cost)

        def _feat_ev(tilt: float) -> float:
            return sum(feat_mass[kind] * _mu(items, tilt) for kind, items in feat_groups.items())

        lo, hi = -16.0, 0.0
        for _ in range(28):
            mid = (lo + hi) / 2.0
            ev = _feat_ev(mid)
            if ev > feat_cap:
                hi = mid
            else:
                lo = mid
            feat_tilt = hi
        feat_ev = _feat_ev(feat_tilt)
        if feat_ev > feat_cap:
            feat_tilt = -16.0
            feat_ev = _feat_ev(feat_tilt)
    remain_mass = max(0.0, 1.0 - p3 - p4 - p_feat)
    remain_ev = TARGET_RTP * cost - bonus_ev - feat_ev
    if remain_ev < 0:
        bonus_tilt = -12.0
        bonus_ev = p3 * _mu(by_class["fg3"], bonus_tilt) + p4 * _mu(by_class["fg4"], bonus_tilt)
        if feat_groups and p_feat > 0:
            feat_tilt = -16.0
            feat_ev = sum(feat_mass[kind] * _mu(items, feat_tilt) for kind, items in feat_groups.items())
        remain_ev = TARGET_RTP * cost - bonus_ev - feat_ev
        remain_mass = max(0.0, 1.0 - p3 - p4 - p_feat)

    # Hits keep a mild cheap tilt so the remaining RTP can still be filled.
    # Empty books take leftover mass and hold the 95% RTP.
    hit_tilt = -1.0
    if by_class["hit"] and remain_ev > 0:
        mu_hit = max(_mu(by_class["hit"], hit_tilt), 0.1)
        if remain_mass * mu_hit + bonus_ev + 1e-12 < TARGET_RTP * cost:
            hit_tilt = 0.0
            mu_hit = max(_mu(by_class["hit"], hit_tilt), 0.1)
        p_hit = min(remain_mass, max(0.0, remain_ev / mu_hit))
    else:
        p_hit = 0.0
        mu_hit = 0.0
    p_hit = min(remain_mass, max(0.0, p_hit))
    if p_hit + p3 + p4 + 1e-12 < HIT_RATE_FLOOR and by_class["hit"]:
        p_hit = min(remain_mass, HIT_RATE_FLOOR - p3 - p4)
    p_zero = max(0.0, remain_mass - p_hit)

    weights: dict[int, int] = {int(book_id): 1 for book_id, _, _ in rows}
    weights.update(_mass_weights(by_class["fg3"], p3, bonus_tilt))
    weights.update(_mass_weights(by_class["fg4"], p4, bonus_tilt))
    if feat_groups and p_feat > 0:
        for kind, items in feat_groups.items():
            weights.update(_mass_weights(items, feat_mass[kind], feat_tilt))
    if by_class["hit"] and p_hit > 0:
        weights.update(_mass_weights(by_class["hit"], p_hit, hit_tilt))
    if by_class["zero"] and p_zero > 0:
        weights.update(_even_weights(by_class["zero"], p_zero))

    out = [(book_id, max(1, weights[int(book_id)]), payouts[int(book_id)]) for book_id, _, _ in rows]
    out = _fit_remain_rtp(out, classes, mode, p3, p4, p_feat)
    gcd = _gcd_many(weight for _, weight, _ in out)
    return [(book_id, max(1, weight // gcd), cents) for book_id, weight, cents in out]


def _fit_remain_rtp(
    rows: list[tuple[int, int, int]],
    classes: dict[int, str],
    mode: str,
    p3: float,
    p4: float,
    p_feat: float = 0.0,
) -> list[tuple[int, int, int]]:
    """Move mass between hits and zeros only. Bonus/feature weights stay fixed."""
    cost = MODE_COST[mode]
    bonus_ids = {
        int(book_id)
        for book_id, kind in classes.items()
        if kind in {"fg3", "fg4", *FEATURE_CLASSES}
    }
    hit_ids = [int(book_id) for book_id, kind in classes.items() if kind == "hit"]
    zero_ids = [int(book_id) for book_id, kind in classes.items() if kind == "zero"]
    by_id = {int(book_id): (weight, cents) for book_id, weight, cents in rows}
    if not hit_ids or not zero_ids:
        return rows
    bonus_w = 0.0
    bonus_e = 0.0
    for book_id in bonus_ids:
        if book_id not in by_id:
            continue
        weight, cents = by_id[book_id]
        bonus_w += weight
        bonus_e += weight * (cents / 100.0)
    bonus_target = p3 + p4 + p_feat
    if bonus_w > 0 and bonus_target > 0:
        remain_w = max(1, int(round(bonus_w * (1.0 - bonus_target) / bonus_target)))
    else:
        remain_w = max(1, int(round((1.0 - bonus_target) * SCALE)))
    hit_rel = {book_id: by_id[book_id][0] for book_id in hit_ids if book_id in by_id}
    hit_rel_sum = sum(hit_rel.values()) or 1
    hit_pay = {book_id: by_id[book_id][1] / 100.0 for book_id in hit_rel}
    zero_n = max(len(zero_ids), 1)

    def parts(p_hit: float) -> tuple[int, int, float]:
        frac = min(1.0, max(0.0, p_hit))
        hit_w = max(0, int(round(remain_w * frac)))
        zero_w = max(0, remain_w - hit_w)
        hit_e = 0.0
        if hit_w:
            for book_id, rel in hit_rel.items():
                hit_e += (hit_w * (rel / hit_rel_sum)) * hit_pay[book_id]
        total_w = bonus_w + hit_w + zero_w
        expected = bonus_e + hit_e
        return hit_w, zero_w, expected / max(total_w, 1e-12) / cost

    lo, hi = 0.0, 1.0
    best = 0.5
    best_err = 1e9
    for _ in range(32):
        mid = (lo + hi) / 2.0
        _hit_w, _zero_w, rtp = parts(mid)
        err = abs(rtp - TARGET_RTP)
        if err < best_err:
            best, best_err = mid, err
        if rtp > TARGET_RTP:
            hi = mid
        else:
            lo = mid
    hit_w, zero_w, _rtp = parts(best)
    weights = {book_id: weight for book_id, weight, _ in rows}
    for book_id, rel in hit_rel.items():
        weights[book_id] = max(1, int(round(hit_w * (rel / hit_rel_sum)))) if hit_w else 1
    each_zero = max(1, int(round(zero_w / zero_n))) if zero_w else 1
    for book_id in zero_ids:
        weights[book_id] = each_zero
    for book_id in bonus_ids:
        if book_id in by_id:
            weights[book_id] = by_id[book_id][0]
    return [(book_id, max(1, weights[int(book_id)]), cents) for book_id, _, cents in rows]


def class_stats(rows: list[tuple[int, int, int]], classes: dict[int, str], mode: str) -> dict:
    cost = MODE_COST[mode]
    total_w = sum(weight for _, weight, _ in rows) or 1
    out = {"rtp": 0.0, "classes": {}}
    expected = 0.0
    grouped: dict[str, list[tuple[int, int]]] = {}
    for book_id, weight, cents in rows:
        kind = classes.get(int(book_id), "hit")
        grouped.setdefault(kind, []).append((weight, cents))
        expected += weight * (cents / 100.0)
    out["rtp"] = expected / total_w / cost
    for kind, items in grouped.items():
        w = sum(weight for weight, _ in items)
        pay = sum(weight * (cents / 100.0) for weight, cents in items)
        out["classes"][kind] = {
            "n": len(items),
            "p": w / total_w,
            "one_in": (total_w / w) if w else None,
            "mu": (pay / w) if w else 0.0,
        }
    return out


def load_lut_rows(path: str) -> list[tuple[int, int, int]]:
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for book_id, weight, payout in csv.reader(handle):
            rows.append((int(book_id), int(weight), int(payout)))
    return rows


def _zstd_lines(raw):
    proc = subprocess.Popen(
        ["zstd", "-d", "-c", "-T0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin and proc.stdout

    def pump():
        assert proc.stdin
        while True:
            chunk = raw.read(1024 * 1024)
            if not chunk:
                break
            proc.stdin.write(chunk)
        proc.stdin.close()

    threading.Thread(target=pump, daemon=True).start()
    for line in proc.stdout:
        yield line
    err = proc.wait()
    if err:
        message = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", "replace")
        raise RuntimeError(f"zstd failed ({err}): {message[:400]}")


def _record_class(classes: dict[int, str], line) -> None:
    if not line.strip():
        return
    book = json.loads(line)
    classes[int(book["id"])] = classify_book(book)
    if len(classes) % 100000 == 0:
        print(f"  classified {len(classes)}", flush=True)


def classify_books_file(path: str) -> dict[int, str]:
    classes: dict[int, str] = {}
    with open(path, "rb") as raw:
        stream = _zstd_lines(raw) if path.endswith(".zst") else raw
        for line in stream:
            _record_class(classes, line)
    return classes


def classify_books_zip(zf: zipfile.ZipFile, inner: str) -> dict[int, str]:
    classes: dict[int, str] = {}
    with zf.open(inner) as raw:
        for line in _zstd_lines(raw):
            _record_class(classes, line)
    return classes


def reweight_mode_rows(
    rows: list[tuple[int, int, int]],
    mode: str,
    classes: dict[int, str],
) -> tuple[list[tuple[int, int, int]], dict]:
    weighted = assign_bonus_freq_weights(rows, mode, classes)
    stats = lut_stats(weighted, mode)
    freq = class_stats(weighted, classes, mode)
    stats.update({"bonus_freq": freq})
    p3 = freq["classes"].get("fg3", {}).get("p", 0.0)
    p4 = freq["classes"].get("fg4", {}).get("p", 0.0)
    want = BONUS_FREQ[mode]
    if abs(p3 - want["fg3"]) / want["fg3"] > 0.08:
        raise ValueError(f"{mode} 3-scatter p={p3:.6f} want {want['fg3']}")
    if abs(p4 - want["fg4"]) / want["fg4"] > 0.08:
        raise ValueError(f"{mode} 4-scatter p={p4:.6f} want {want['fg4']}")
    p_feat = sum(freq["classes"].get(kind, {}).get("p", 0.0) for kind in FEATURE_CLASSES)
    if p_feat and abs(p_feat - FEATURE_RATE) / FEATURE_RATE > 0.08:
        raise ValueError(f"{mode} feature p={p_feat:.6f} want {FEATURE_RATE}")
    p_sync = freq["classes"].get("feature_sync", {}).get("p", 0.0)
    if p_feat and abs(p_sync - 0.5 * FEATURE_RATE) / (0.5 * FEATURE_RATE) > 0.12:
        raise ValueError(f"{mode} sync p={p_sync:.6f} want {0.5 * FEATURE_RATE}")
    if not (TARGET_RTP - RTP_TOL * 2 <= stats["rtp"] <= TARGET_RTP + RTP_TOL * 2):
        raise ValueError(f"{mode} RTP {stats['rtp']:.4f} outside {TARGET_RTP} window")
    return weighted, stats


def reweight_zip(src_zip: str, dst_zip: str | None = None) -> dict:
    prefix = "Sunset Stereo/math/"
    src_zip = os.path.abspath(src_zip)
    dst_zip = os.path.abspath(dst_zip or src_zip)
    if dst_zip != src_zip:
        raise ValueError("update the existing math zip in place; copying 1.3G is not supported")
    summary = {}
    work = os.path.join(os.path.dirname(src_zip) or ".", ".bonus-freq-lut")
    os.makedirs(os.path.join(work, prefix), exist_ok=True)
    with zipfile.ZipFile(src_zip, "r") as zf:
        for mode in ("base", "scatter"):
            lut_name = f"{prefix}lookUpTable_{mode}_0.csv"
            books_name = f"{prefix}books_{mode}.jsonl.zst"
            raw = zf.read(lut_name).decode("utf-8")
            rows = [
                (int(book_id), int(weight), int(payout))
                for book_id, weight, payout in csv.reader(io.StringIO(raw))
            ]
            print(f"classify {mode} books…", flush=True)
            classes = classify_books_zip(zf, books_name)
            print(f"reweight {mode}…", flush=True)
            weighted, stats = reweight_mode_rows(rows, mode, classes)
            path = os.path.join(work, lut_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                for book_id, weight, cents in weighted:
                    handle.write(f"{int(book_id)},{int(weight)},{int(cents)}\n")
            summary[mode] = {
                "rtp": stats["rtp"],
                "hit_rate": stats["hit_rate"],
                "fg3": stats["bonus_freq"]["classes"].get("fg3"),
                "fg4": stats["bonus_freq"]["classes"].get("fg4"),
                "feature": {
                    kind: stats["bonus_freq"]["classes"].get(kind)
                    for kind in FEATURE_CLASSES
                    if stats["bonus_freq"]["classes"].get(kind)
                },
                "zero": stats["bonus_freq"]["classes"].get("zero"),
            }
            print(f"{mode} {summary[mode]}", flush=True)
    print("update zip LUTs…", flush=True)
    subprocess.check_call(
        ["zip", "-q", "-u", src_zip, f"{prefix}lookUpTable_base_0.csv", f"{prefix}lookUpTable_scatter_0.csv"],
        cwd=work,
    )
    return summary


def reweight_publish_dir(publish_dir: str, modes: Iterable[str] = ("base", "scatter")) -> dict:
    summary = {}
    for mode in modes:
        lut_path = os.path.join(publish_dir, f"lookUpTable_{mode}_0.csv")
        books = os.path.join(publish_dir, f"books_{mode}.jsonl.zst")
        if not os.path.isfile(lut_path) or not os.path.isfile(books):
            raise FileNotFoundError(mode)
        rows = load_lut_rows(lut_path)
        classes = classify_books_file(books)
        weighted, stats = reweight_mode_rows(rows, mode, classes)
        write_lut(lut_path, weighted)
        summary[mode] = stats
        print(f"wrote {lut_path} rtp={stats['rtp']:.4f}")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    print(json.dumps(reweight_zip(args.zip, args.out), indent=2))
