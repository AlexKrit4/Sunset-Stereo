"""Reweight the 95× buy-bonus LUT.

Book payouts stay in 1× stake units (LUT cents). Mode cost is 95, so
RTP = E[payout_1x] / 95. Target 95% → E ≈ 90.25.

75% of weight sits on books that do not recoup the buy (payout < 95×).
25% recoups. Probability is spread across Engine hit-rate ranges so one
200–500× pocket cannot carry almost all of the RTP.
"""

from __future__ import annotations

import csv
import math
import os
from typing import Iterable

from game_config import BUY_BONUS_COST

DEAD_MASS = 0.75
RECOUP_MASS = 0.25
WINCAP_MASS = 0.0001
TARGET_RTP = 0.95
RTP_TOLERANCE = 0.01
MAX_RANGE_RTP = 0.22

# Stake Engine hit-rate bins, split at the 95× buy so dead/recoup stay separate.
RANGES = [
    (0.0, 0.1),
    (0.1, 1.0),
    (1.0, 5.0),
    (5.0, 10.0),
    (10.0, 20.0),
    (20.0, 50.0),
    (50.0, 95.0),
    (95.0, 200.0),
    (200.0, 500.0),
    (500.0, 1000.0),
    (1000.0, 2000.0),
    (2000.0, 5000.0),
    (5000.0, 10000.0),
    (10000.0, 15000.0001),
]

# Probability mix for dead (<95×) books. Zeros contribute no RTP, so they
# cannot be derived from TARGET_RTP_SHARE.
DEAD_TARGET_MASS = {
    (0.0, 0.1): 0.18,
    (0.1, 1.0): 0.10,
    (1.0, 5.0): 0.10,
    (5.0, 10.0): 0.07,
    (10.0, 20.0): 0.07,
    (20.0, 50.0): 0.13,
    (50.0, 95.0): 0.10,
}


def _gcd_many(values: Iterable[int]) -> int:
    acc = 0
    for value in values:
        acc = math.gcd(acc, int(value))
        if acc == 1:
            return 1
    return max(acc, 1)


def classify(payout_cents: int) -> str:
    payout = payout_cents / 100.0
    if payout >= 15000.0 - 1e-9:
        return "wincap"
    if payout >= BUY_BONUS_COST:
        return "recoup"
    return "dead"


def payout_range(payout_1x: float) -> tuple[float, float] | None:
    if payout_1x >= 15000.0 - 1e-9:
        return None
    for lo, hi in RANGES:
        if lo <= payout_1x < hi:
            return (lo, hi)
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


def rtp_by_range(rows: list[tuple[int, int, int]]) -> dict[tuple[float, float], float]:
    total_w = sum(weight for _, weight, _ in rows) or 1
    contrib: dict[tuple[float, float], float] = {key: 0.0 for key in RANGES}
    wincap = 0.0
    for _, weight, cents in rows:
        payout = cents / 100.0
        share = weight * payout / total_w / BUY_BONUS_COST
        key = payout_range(payout)
        if key is None:
            wincap += share
        else:
            contrib[key] += share
    contrib[(15000.0, 15000.0)] = wincap
    return contrib


def _range_mean(books: list[tuple[int, int]]) -> float:
    return sum(cents for _, cents in books) / (100.0 * len(books))


def _scale_group(mass: dict, keys: list, target: float) -> None:
    total = sum(mass[key] for key in keys)
    if total <= 0 or not keys:
        return
    factor = target / total
    for key in keys:
        mass[key] *= factor


def _dead_mass(by_range: dict) -> dict[tuple[float, float], float]:
    mass = {key: 0.0 for key in RANGES}
    dead_keys = [key for key in RANGES if key[1] <= 95.0 and by_range[key]]
    leftover = 0.0
    for key, target in DEAD_TARGET_MASS.items():
        if by_range.get(key):
            mass[key] = target
        else:
            leftover += target
    if leftover and dead_keys:
        add = leftover / len(dead_keys)
        for key in dead_keys:
            mass[key] += add
    _scale_group(mass, dead_keys, DEAD_MASS)
    return mass


def _allocate_recoup(by_range: dict, dead_e: float) -> dict[tuple[float, float], float]:
    """Put recoup probability on the lowest bin first, then climb until RTP hits 95%."""
    mass = {key: 0.0 for key in RANGES}
    recoup_keys = [key for key in RANGES if key[0] >= 95.0 and by_range[key]]
    if not recoup_keys:
        return mass
    remaining = RECOUP_MASS - WINCAP_MASS
    target_e = TARGET_RTP * BUY_BONUS_COST - dead_e - WINCAP_MASS * 15000.0
    low = recoup_keys[0]
    mass[low] = remaining
    current_e = remaining * _range_mean(by_range[low])
    for key in recoup_keys[1:]:
        if current_e >= target_e:
            break
        mean_low = _range_mean(by_range[low])
        mean = _range_mean(by_range[key])
        if mean <= mean_low + 1e-6:
            continue
        need = target_e - current_e
        max_mass = MAX_RANGE_RTP * BUY_BONUS_COST / mean
        movable = min(need / (mean - mean_low), max_mass, mass[low] * 0.95)
        if movable <= 1e-12:
            continue
        mass[low] -= movable
        mass[key] = movable
        current_e += movable * (mean - mean_low)
    return mass


def assign_weights(rows: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    buckets = {"dead": [], "recoup": [], "wincap": []}
    by_range: dict[tuple[float, float], list[tuple[int, int]]] = {key: [] for key in RANGES}
    for book_id, _, cents in rows:
        kind = classify(cents)
        buckets[kind].append((book_id, cents))
        key = payout_range(cents / 100.0)
        if key is not None:
            by_range[key].append((book_id, cents))

    if not buckets["dead"] or not buckets["recoup"]:
        raise ValueError("bonus LUT needs both dead (<95×) and recoup (≥95×) books")

    mass = _dead_mass(by_range)
    dead_e = sum(
        mass[key] * _range_mean(books)
        for key, books in by_range.items()
        if key[1] <= 95.0 and books and mass.get(key, 0) > 0
    )
    recoup_mass = _allocate_recoup(by_range, dead_e)
    for key, value in recoup_mass.items():
        if key[0] >= 95.0:
            mass[key] = value

    scale = 1_000_000_000
    weights: dict[int, int] = {book_id: 1 for book_id, _, _ in rows}
    for key, books in by_range.items():
        if not books or mass.get(key, 0) <= 0:
            continue
        each = max(1, int(round((mass[key] / len(books)) * scale)))
        for book_id, _ in books:
            weights[book_id] = each
    if buckets["wincap"]:
        wincap_each = max(1, int(round((WINCAP_MASS / len(buckets["wincap"])) * scale)))
        for book_id, _ in buckets["wincap"]:
            weights[book_id] = wincap_each

    gcd = _gcd_many(weights.values())
    return [(book_id, max(1, weights[book_id] // gcd), cents) for book_id, _, cents in rows]


def lut_stats(rows: list[tuple[int, int, int]]) -> dict[str, float]:
    total_w = sum(weight for _, weight, _ in rows)
    expected = sum(weight * (cents / 100.0) for _, weight, cents in rows) / total_w
    mass = {"dead": 0.0, "recoup": 0.0, "wincap": 0.0}
    hit = 0.0
    for _, weight, cents in rows:
        mass[classify(cents)] += weight / total_w
        if cents > 0:
            hit += weight / total_w
    contrib = rtp_by_range(rows)
    recoup_contrib = {key: value for key, value in contrib.items() if key[0] >= 95.0 and key != (15000.0, 15000.0)}
    peak = max(recoup_contrib.values(), default=0.0)
    spread = sum(1 for value in recoup_contrib.values() if value >= 0.03)
    return {
        "rtp": expected / BUY_BONUS_COST,
        "expected": expected,
        "dead_mass": mass["dead"],
        "recoup_mass": mass["recoup"] + mass["wincap"],
        "wincap_mass": mass["wincap"],
        "hit_rate": hit,
        "books": float(len(rows)),
        "total_weight": float(total_w),
        "peak_range_rtp": peak,
        "recoup_ranges_used": float(spread),
    }


def write_lut(path: str, rows: list[tuple[int, int, int]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for book_id, weight, cents in rows:
            writer.writerow([book_id, weight, cents])


def weight_bonus_lookup(publish_dir: str) -> dict[str, float]:
    source = os.path.join(publish_dir, "lookUpTable_bonus.csv")
    if not os.path.isfile(source):
        source = os.path.join(
            os.path.dirname(publish_dir),
            "lookup_tables",
            "lookUpTable_bonus.csv",
        )
    dest = os.path.join(publish_dir, "lookUpTable_bonus_0.csv")
    rows = assign_weights(load_lut(source))
    write_lut(dest, rows)
    stats = lut_stats(rows)
    if not (TARGET_RTP - RTP_TOLERANCE <= stats["rtp"] <= TARGET_RTP + RTP_TOLERANCE):
        raise ValueError(f"bonus RTP {stats['rtp']:.4f} outside 95% ± 1%")
    if abs(stats["dead_mass"] - DEAD_MASS) > 0.02:
        raise ValueError(f"dead mass {stats['dead_mass']:.4f} is not 75%")
    if abs(stats["recoup_mass"] - RECOUP_MASS) > 0.02:
        raise ValueError(f"recoup mass {stats['recoup_mass']:.4f} is not 25%")
    if stats["hit_rate"] < 1 / 50:
        raise ValueError(f"non-zero hit rate {stats['hit_rate']:.4f} is worse than 1/50")
    if stats["peak_range_rtp"] > 0.40:
        raise ValueError(f"one hit-rate range carries {stats['peak_range_rtp']:.2%} of RTP")
    return stats


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    publish = os.path.join(here, "library", "publish_files")
    stats = weight_bonus_lookup(publish)
    print("bonus LUT", stats)
