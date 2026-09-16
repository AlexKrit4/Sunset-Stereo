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
MAX_RANGE_RTP = 0.18
WINCAP_MASS = {"base": 0.00002, "scatter": 0.00002, "bonus": 0.00008, "wildbonus": 0.00012}


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


def assign_weights(rows: list[tuple[int, int, int]], mode: str) -> list[tuple[int, int, int]]:
    cost = MODE_COST[mode]
    target_e = TARGET_RTP * cost
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

    mass = {key: 0.0 for key in targets}
    leftover = 0.0
    for key, target in targets.items():
        if buckets.get(key) or (key[0] >= 10000 and buckets["wincap"]):
            mass[key] = target
        else:
            leftover += target
    live = [key for key, books in buckets.items() if key != "wincap" and books]
    if leftover and live:
        add = leftover / len(live)
        for key in live:
            mass[key] += add
    total_mass = sum(mass.values()) + (WINCAP_MASS[mode] if buckets["wincap"] else 0.0)
    if total_mass <= 0:
        raise ValueError(f"{mode} has empty weight buckets")
    scale_mass = 1.0 / total_mass
    for key in mass:
        mass[key] *= scale_mass
    wincap_mass = WINCAP_MASS[mode] * scale_mass if buckets["wincap"] else 0.0
    live_pay = [key for key in live if key != (0.0, 0.1)]
    zero_key = (0.0, 0.1)
    zero_mass = mass.get(zero_key, 0.0)
    pay_mass = max(0.0, 1.0 - zero_mass - wincap_mass)
    means = {
        key: sum(cents for _, cents in buckets[key]) / (100.0 * len(buckets[key]))
        for key in live_pay
    }
    ordered = sorted(live_pay, key=lambda key: means[key])
    for key in live_pay:
        mass[key] = 0.0
    if ordered:
        mass[ordered[0]] = pay_mass
        target_from_pay = max(0.0, TARGET_RTP * cost - wincap_mass * 15000.0)
        current = pay_mass * means[ordered[0]]
        for src, dest in zip(ordered, ordered[1:]):
            if current >= target_from_pay:
                break
            gap = means[dest] - means[src]
            if gap <= 1e-9:
                continue
            need = target_from_pay - current
            movable = min(mass[src], need / gap)
            mass[src] -= movable
            mass[dest] += movable
            current += movable * gap


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
    return [(book_id, max(1, weights[book_id] // gcd), cents) for book_id, _, cents in rows]


def lut_stats(rows: list[tuple[int, int, int]], mode: str) -> dict[str, float]:
    return _stats(rows, MODE_COST[mode])


def weight_mode_lookup(publish_dir: str, mode: str, lookup_dir: str | None = None) -> dict[str, float]:
    source = os.path.join(lookup_dir or os.path.join(os.path.dirname(publish_dir), "lookup_tables"), f"lookUpTable_{mode}.csv")
    if not os.path.isfile(source):
        source = os.path.join(publish_dir, f"lookUpTable_{mode}.csv")
    dest = os.path.join(publish_dir, f"lookUpTable_{mode}_0.csv")
    rows = assign_weights(load_lut(source), mode)
    write_lut(dest, rows)
    stats = lut_stats(rows, mode)
    if not (TARGET_RTP - RTP_TOL * 2 <= stats["rtp"] <= TARGET_RTP + RTP_TOL * 2):
        raise ValueError(f"{mode} RTP {stats['rtp']:.4f} outside {TARGET_RTP} window")
    if stats["hit_rate"] + 1e-9 < 1 / 50:
        raise ValueError(f"{mode} hit-rate {stats['hit_rate']:.4f} is worse than 1/50")
    if stats["unique_payouts"] < 50:
        raise ValueError(f"{mode} only {stats['unique_payouts']:.0f} unique payouts")
    return stats
