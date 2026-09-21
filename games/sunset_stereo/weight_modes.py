"""Weight every Sunset Stereo mode so RTP sits on a diverse payout mix.

Books stay unique (min weight 1). Probability is spread across Engine
hit-rate ranges so one 200–500× pocket cannot carry the RTP.
"""

from __future__ import annotations

import csv
import math
import os
from typing import Iterable

RANGES = [
    (0.0, 0.1),
    (0.1, 1.0),
    (1.0, 2.0),
    (2.0, 5.0),
    (5.0, 10.0),
    (10.0, 20.0),
    (20.0, 50.0),
    (50.0, 100.0),
    (100.0, 200.0),
    (200.0, 500.0),
    (500.0, 1000.0),
    (1000.0, 2000.0),
    (2000.0, 5000.0),
    (5000.0, 10000.0),
    (10000.0, 15000.0001),
]

MODE_COST = {"base": 1.0, "scatter": 1.5, "bonus": 95.0, "wildbonus": 225.0}
TARGET_RTP = 0.95
RTP_TOL = 0.004
HIT_RATE = {"base": 0.25, "scatter": 0.35, "bonus": 1.0, "wildbonus": 1.0}
MAX_RANGE_RTP = 0.16
WINCAP_MASS = {"base": 0.0000008, "scatter": 0.0000008, "bonus": 0.0000005, "wildbonus": 0.0000006}


def _gcd_many(values: Iterable[int]) -> int:
    acc = 0
    for value in values:
        acc = math.gcd(acc, int(value))
        if acc == 1:
            return 1
    return max(acc, 1)


def payout_range(payout_1x: float) -> tuple[float, float] | None:
    if payout_1x >= 15000.0 - 1e-9:
        return None
    for lo, hi in RANGES:
        if lo <= payout_1x < hi:
            return lo, hi
    return RANGES[-1]


def load_lut(path: str) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for book_id, _weight, payout in csv.reader(handle):
            cents = int(payout)
            if cents % 10 != 0:
                raise ValueError(f"LUT payout {cents} is not a tenth of 1×")
            rows.append((int(book_id), 1, cents))
    return rows


def write_lut(path: str, rows: list[tuple[int, int, int]]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for book_id, weight, cents in rows:
            handle.write(f"{int(book_id)},{int(weight)},{int(cents)}\n")


def _stats(rows: list[tuple[int, int, int]], cost: float) -> dict[str, float]:
    total_w = sum(weight for _, weight, _ in rows) or 1
    expected = sum(weight * (cents / 100.0) for _, weight, cents in rows) / total_w
    hit = sum(weight for _, weight, cents in rows if cents > 0) / total_w
    payouts = {cents for _, _, cents in rows}
    contrib: dict[tuple[float, float], float] = {key: 0.0 for key in RANGES}
    wincap = 0.0
    for _, weight, cents in rows:
        payout = cents / 100.0
        share = weight * payout / total_w / cost
        key = payout_range(payout)
        if key is None:
            wincap += share
        else:
            contrib[key] += share
    peak = max(list(contrib.values()) + [wincap])
    items = sorted(rows, key=lambda row: -row[2])
    need = 0.001 * total_w
    acc_w = 0.0
    acc_pay = 0.0
    for _, weight, cents in items:
        take = min(weight, need - acc_w)
        acc_pay += take * (cents / 100.0)
        acc_w += take
        if acc_w >= need - 1e-12:
            break
    cvar_abs = acc_pay / max(acc_w, 1e-12)
    etl40 = sum(weight * (cents / 100.0) for _, weight, cents in rows if cents / 100.0 > 40 * cost) / total_w / cost
    etl10k = sum(weight * (cents / 100.0) for _, weight, cents in rows if cents / 100.0 > 10000 * cost) / total_w / cost
    p5k = sum(weight for _, weight, cents in rows if cents / 100.0 >= 5000) / total_w
    p10k = sum(weight for _, weight, cents in rows if cents / 100.0 >= 10000) / total_w
    mean = expected
    second = sum(weight * (cents / 100.0) ** 2 for _, weight, cents in rows) / total_w
    std = math.sqrt(max(0.0, second - mean * mean))
    return {
        "rtp": expected / cost,
        "expected": expected,
        "hit_rate": hit,
        "unique_payouts": float(len(payouts)),
        "peak_range_rtp": peak,
        "cvar_abs": cvar_abs,
        "cvar_stake": cvar_abs / cost,
        "etl40": etl40,
        "etl10k": etl10k,
        "p5k": p5k,
        "p10k": p10k,
        "std": std,
        "books": float(len(rows)),
    }


def _range_mass_targets(mode: str) -> dict[tuple[float, float], float]:
    """Probability mass per Engine hit-rate bin, including zeros in (0, 0.1)."""
    if mode == "base":
        return {
            (0.0, 0.1): 0.75,
            (0.1, 1.0): 0.10,
            (1.0, 2.0): 0.06,
            (2.0, 5.0): 0.06,
            (5.0, 10.0): 0.012,
            (10.0, 20.0): 0.008,
            (20.0, 50.0): 0.004,
            (50.0, 100.0): 0.003,
            (100.0, 200.0): 0.0018,
            (200.0, 500.0): 0.0008,
            (500.0, 1000.0): 0.00025,
            (1000.0, 2000.0): 0.00008,
            (2000.0, 5000.0): 0.00004,
            (5000.0, 10000.0): 0.00002,
            (10000.0, 15000.0001): 0.00001,
        }
    if mode == "scatter":
        return {
            (0.0, 0.1): 0.65,
            (0.1, 1.0): 0.12,
            (1.0, 2.0): 0.08,
            (2.0, 5.0): 0.08,
            (5.0, 10.0): 0.025,
            (10.0, 20.0): 0.02,
            (20.0, 50.0): 0.012,
            (50.0, 100.0): 0.008,
            (100.0, 200.0): 0.003,
            (200.0, 500.0): 0.0012,
            (500.0, 1000.0): 0.0004,
            (1000.0, 2000.0): 0.0002,
            (2000.0, 5000.0): 0.0001,
            (5000.0, 10000.0): 0.00005,
            (10000.0, 15000.0001): 0.00003,
        }
    if mode == "bonus":
        return {
            (0.0, 0.1): 0.0,
            (0.1, 1.0): 0.0,
            (1.0, 2.0): 0.0,
            (2.0, 5.0): 0.08,
            (5.0, 10.0): 0.12,
            (10.0, 20.0): 0.16,
            (20.0, 50.0): 0.26,
            (50.0, 100.0): 0.20,
            (100.0, 200.0): 0.09,
            (200.0, 500.0): 0.05,
            (500.0, 1000.0): 0.022,
            (1000.0, 2000.0): 0.01,
            (2000.0, 5000.0): 0.005,
            (5000.0, 10000.0): 0.002,
            (10000.0, 15000.0001): 0.001,
        }
    return {
        (0.0, 0.1): 0.0,
        (0.1, 1.0): 0.0,
        (1.0, 2.0): 0.0,
        (2.0, 5.0): 0.04,
        (5.0, 10.0): 0.10,
        (10.0, 20.0): 0.16,
        (20.0, 50.0): 0.22,
        (50.0, 100.0): 0.18,
        (100.0, 200.0): 0.12,
        (200.0, 500.0): 0.09,
        (500.0, 1000.0): 0.05,
        (1000.0, 2000.0): 0.022,
        (2000.0, 5000.0): 0.012,
        (5000.0, 10000.0): 0.004,
        (10000.0, 15000.0001): 0.002,
    }


def _bucket_means(buckets: dict, keys: list[tuple[float, float]]) -> dict[tuple[float, float], float]:
    means = {}
    for key in keys:
        books = buckets[key]
        means[key] = sum(cents for _, cents in books) / (100.0 * len(books))
    return means


def _rtp_from_mass(mass: dict, means: dict, wincap_mass: float, cost: float) -> float:
    expected = sum(mass.get(key, 0.0) * means[key] for key in means)
    expected += wincap_mass * 15000.0
    return expected / cost


def _clip_range_rtp(mass: dict, means: dict, cost: float, sink_key: tuple[float, float]) -> None:
    """Cap per-bin RTP by sending leftover probability to zeros or the cheapest hits."""
    for key in list(mass):
        if key == sink_key or key not in means or mass[key] <= 0:
            continue
        contrib = mass[key] * means[key] / cost
        if contrib <= MAX_RANGE_RTP + 1e-9:
            continue
        keep = MAX_RANGE_RTP * cost / max(means[key], 1e-9)
        extra = mass[key] - keep
        mass[key] = keep
        mass[sink_key] = mass.get(sink_key, 0.0) + extra


def assign_weights(
    rows: list[tuple[int, int, int]],
    mode: str,
    classes: dict[int, str] | None = None,
) -> list[tuple[int, int, int]]:
    if classes and mode in {"base", "scatter"}:
        from bonus_freq import assign_bonus_freq_weights

        return assign_bonus_freq_weights(rows, mode, classes)
    cost = MODE_COST[mode]
    targets = _range_mass_targets(mode)
    buckets: dict[tuple[float, float] | str, list[tuple[int, int]]] = {key: [] for key in RANGES}
    buckets["wincap"] = []
    for book_id, _, cents in rows:
        payout = cents / 100.0
        if payout >= 15000.0 - 1e-9:
            buckets["wincap"].append((book_id, cents))
        else:
            key = payout_range(payout) or RANGES[0]
            buckets[key].append((book_id, cents))

    live_pay = [key for key in RANGES if key != (0.0, 0.1) and buckets[key]]
    zero_key = (0.0, 0.1)
    has_zero = bool(buckets[zero_key])
    if not live_pay:
        raise ValueError(f"{mode} has no paying books to weight")
    means = _bucket_means(buckets, live_pay)
    wincap_mass = WINCAP_MASS[mode] if buckets["wincap"] else 0.0
    zero_mass = targets.get(zero_key, 0.0) if has_zero else 0.0
    pay_mass = max(0.0, 1.0 - zero_mass - wincap_mass)
    shape = {key: targets.get(key, 0.0) for key in live_pay}
    if sum(shape.values()) <= 0:
        shape = {key: 1.0 for key in live_pay}

    def masses_for_tilt(tilt: float) -> dict[tuple[float, float], float]:
        raw = {}
        for key in live_pay:
            raw[key] = max(shape[key], 1e-9) * (max(means[key], 0.05) ** tilt)
        total = sum(raw.values()) or 1.0
        out: dict[tuple[float, float], float] = {zero_key: zero_mass} if has_zero else {}
        for key in live_pay:
            out[key] = pay_mass * raw[key] / total
        return out

    lo, hi = -6.0, 6.0
    tilt = 0.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        rtp = _rtp_from_mass(masses_for_tilt(mid), means, wincap_mass, cost)
        tilt = mid
        if rtp > TARGET_RTP:
            hi = mid
        else:
            lo = mid
    sink_key = zero_key if has_zero else min(live_pay, key=lambda key: means[key])
    mass = masses_for_tilt(tilt)
    _clip_range_rtp(mass, means, cost, sink_key)
    rtp = _rtp_from_mass(mass, means, wincap_mass, cost)
    if rtp + 1e-9 < TARGET_RTP:
        ordered = sorted(live_pay, key=lambda key: means[key])
        for key in ordered:
            room = MAX_RANGE_RTP * cost - mass.get(key, 0.0) * means[key]
            if room <= 0 or key == sink_key:
                continue
            need = TARGET_RTP * cost - _rtp_from_mass(mass, means, wincap_mass, cost) * cost
            if need <= 0:
                break
            add = min(mass.get(sink_key, 0.0), need / means[key], room / means[key])
            if add <= 0:
                continue
            mass[key] = mass.get(key, 0.0) + add
            mass[sink_key] = mass.get(sink_key, 0.0) - add
    rtp = _rtp_from_mass(mass, means, wincap_mass, cost)
    if abs(rtp - TARGET_RTP) > RTP_TOL:
        ordered = sorted(live_pay, key=lambda key: means[key])
        low, high = ordered[0], ordered[-1]
        gap = means[high] - means[low]
        if gap > 1e-9:
            delta = (TARGET_RTP * cost - rtp * cost) / gap
            if rtp < TARGET_RTP:
                take = min(mass[low], max(0.0, delta))
                mass[low] -= take
                mass[high] += take
            else:
                take = min(mass[high], max(0.0, -delta))
                mass[high] -= take
                mass[low] += take


    scale = 1_000_000_000
    weights: dict[int, int] = {book_id: 1 for book_id, _, _ in rows}
    for key, books in buckets.items():
        if key == "wincap" or not books:
            continue
        share = mass.get(key, 0.0)
        if share <= 0:
            continue
        each = max(1, int(round((share / len(books)) * scale)))
        for book_id, _ in books:
            weights[book_id] = each
    if buckets["wincap"]:
        each = max(1, int(round((wincap_mass / len(buckets["wincap"])) * scale)))
        for book_id, _ in buckets["wincap"]:
            weights[book_id] = each
    gcd = _gcd_many(weights.values())
    out = [(book_id, max(1, weights[book_id] // gcd), cents) for book_id, _, cents in rows]
    return _finalize_weights(out, mode)


def _finalize_weights(rows: list[tuple[int, int, int]], mode: str) -> list[tuple[int, int, int]]:
    """Lock RTP onto 95% after integer weights so modes stay within 0.5%."""
    cost = MODE_COST[mode]
    knob_ids = {
        book_id
        for book_id, _, cents in rows
        if cents / 100.0 < min(40.0 * cost, 500.0)
    }
    if not knob_ids:
        knob_ids = {book_id for book_id, _, cents in rows if cents > 0}
    knob_w = sum(weight for book_id, weight, _ in rows if book_id in knob_ids)
    knob_e = sum(weight * (cents / 100.0) for book_id, weight, cents in rows if book_id in knob_ids)
    rest_w = sum(weight for book_id, weight, _ in rows if book_id not in knob_ids)
    rest_e = sum(weight * (cents / 100.0) for book_id, weight, cents in rows if book_id not in knob_ids)

    def rtp_at(mult: float) -> float:
        total_w = rest_w + knob_w * mult
        expected = rest_e + knob_e * mult
        return expected / max(total_w, 1e-12) / cost

    best_m = 1.0
    best_err = abs(rtp_at(1.0) - TARGET_RTP)
    for step in list(range(4, 481, 4)) + list(range(70, 141)):
        mult = step / 100.0
        err = abs(rtp_at(mult) - TARGET_RTP)
        if err < best_err:
            best_m, best_err = mult, err
    out = []
    for book_id, weight, cents in rows:
        if book_id in knob_ids:
            weight = max(1, int(round(weight * best_m)))
        out.append((book_id, weight, cents))
    gcd = _gcd_many(weight for _, weight, _ in out)
    return [(book_id, max(1, weight // gcd), cents) for book_id, weight, cents in out]


def lut_stats(rows: list[tuple[int, int, int]], mode: str) -> dict[str, float]:
    return _stats(rows, MODE_COST[mode])


def weight_mode_lookup(publish_dir: str, mode: str, lookup_dir: str | None = None) -> dict[str, float]:
    source = os.path.join(lookup_dir or os.path.join(os.path.dirname(publish_dir), "lookup_tables"), f"lookUpTable_{mode}.csv")
    if not os.path.isfile(source):
        source = os.path.join(publish_dir, f"lookUpTable_{mode}.csv")
    dest = os.path.join(publish_dir, f"lookUpTable_{mode}_0.csv")
    rows = load_lut(source)
    classes = None
    books = os.path.join(publish_dir, f"books_{mode}.jsonl.zst")
    if not os.path.isfile(books):
        books = os.path.join(publish_dir, f"books_{mode}.jsonl")
    if mode in {"base", "scatter"} and os.path.isfile(books):
        from bonus_freq import classify_books_file

        classes = classify_books_file(books)
    rows = assign_weights(rows, mode, classes)
    write_lut(dest, rows)
    stats = lut_stats(rows, mode)
    if not (TARGET_RTP - RTP_TOL * 2 <= stats["rtp"] <= TARGET_RTP + RTP_TOL * 2):
        raise ValueError(f"{mode} RTP {stats['rtp']:.4f} outside {TARGET_RTP} window")
    if stats["hit_rate"] + 1e-9 < 1 / 50:
        raise ValueError(f"{mode} hit-rate {stats['hit_rate']:.4f} is worse than 1/50")
    if stats["unique_payouts"] < 50:
        raise ValueError(f"{mode} only {stats['unique_payouts']:.0f} unique payouts")
    if len(rows) >= 900_000 and stats["unique_payouts"] < 3_000:
        raise ValueError(f"{mode} only {stats['unique_payouts']:.0f} unique payouts, need 3000")
    if 200_000 <= len(rows) < 900_000 and stats["unique_payouts"] < 8_000:
        raise ValueError(f"{mode} only {stats['unique_payouts']:.0f} unique payouts, need 8000")
    if mode in {"base", "scatter"} and classes:
        from bonus_freq import BONUS_FREQ, class_stats

        freq = class_stats(rows, classes, mode)
        want = BONUS_FREQ[mode]
        p3 = freq["classes"].get("fg3", {}).get("p", 0.0)
        p4 = freq["classes"].get("fg4", {}).get("p", 0.0)
        if abs(p3 - want["fg3"]) / want["fg3"] > 0.08:
            raise ValueError(f"{mode} 3-scatter p={p3:.6f} want {want['fg3']}")
        if abs(p4 - want["fg4"]) / want["fg4"] > 0.08:
            raise ValueError(f"{mode} 4-scatter p={p4:.6f} want {want['fg4']}")
        stats["fg3"] = freq["classes"].get("fg3", {}).get("one_in")
        stats["fg4"] = freq["classes"].get("fg4", {}).get("one_in")
    return stats
