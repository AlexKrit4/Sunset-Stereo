"""Reweight the 95× buy-bonus LUT.

Book payouts stay in 1× stake units (LUT cents). Mode cost is 95, so
RTP = E[payout_1x] / 95. Target 95% → E ≈ 90.25.

75% of weight sits on books that do not recoup the buy (payout < 95×).
25% recoups (including an extremely rare 15000× tail).
"""

from __future__ import annotations

import csv
import math
import os
from typing import Iterable

from game_config import BUY_BONUS_COST

DEAD_MASS = 0.75
RECOUP_MASS = 0.25
# About 1 in 10_000 bonus buys hit the 15000× ceiling.
WINCAP_MASS = 0.0001
TARGET_RTP = 0.95
RTP_TOLERANCE = 0.01


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


def load_lut(path: str) -> list[tuple[int, int, int]]:
    rows: list[tuple[int, int, int]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for book_id, _weight, payout in csv.reader(handle):
            cents = int(payout)
            if cents % 10 != 0:
                raise ValueError(f"LUT payout {cents} is not a tenth of 1×")
            rows.append((int(book_id), 1, cents))
    return rows


def assign_weights(rows: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    buckets = {"dead": [], "recoup": [], "wincap": []}
    for book_id, _, cents in rows:
        buckets[classify(cents)].append((book_id, cents))

    if not buckets["dead"] or not buckets["recoup"]:
        raise ValueError("bonus LUT needs both dead (<95×) and recoup (≥95×) books")

    wincap_mass = WINCAP_MASS if buckets["wincap"] else 0.0
    recoup_mass = RECOUP_MASS - wincap_mass
    if recoup_mass <= 0:
        raise ValueError("wincap mass consumed the recoup bucket")

    dead_mean = sum(cents for _, cents in buckets["dead"]) / (100.0 * len(buckets["dead"]))
    wincap_pay = 15000.0
    target_e = TARGET_RTP * BUY_BONUS_COST
    recoup_target = (target_e - DEAD_MASS * dead_mean - wincap_mass * wincap_pay) / recoup_mass
    recoup_target = min(max(recoup_target, BUY_BONUS_COST), 14999.9)

    recoup_payouts = [cents / 100.0 for _, cents in buckets["recoup"]]
    recoup_rel = _barbell_to_mean(recoup_payouts, recoup_target)

    scale = 10_000_000
    weights: dict[int, int] = {}
    dead_each = max(1, int(round((DEAD_MASS / len(buckets["dead"])) * scale)))
    for book_id, _ in buckets["dead"]:
        weights[book_id] = dead_each
    recoup_rel_sum = sum(recoup_rel)
    for (book_id, _), rel in zip(buckets["recoup"], recoup_rel):
        weights[book_id] = max(1, int(round(recoup_mass * scale * (rel / recoup_rel_sum))))
    if buckets["wincap"]:
        wincap_each = max(1, int(round((wincap_mass / len(buckets["wincap"])) * scale)))
        for book_id, _ in buckets["wincap"]:
            weights[book_id] = wincap_each

    gcd = _gcd_many(weights.values())
    out = []
    for book_id, _, cents in rows:
        out.append((book_id, weights[book_id] // gcd, cents))
    return out


def _barbell_to_mean(payouts: list[float], target: float) -> list[float]:
    """Almost all mass on two recoup books that bracket the target mean."""
    n = len(payouts)
    weights = [1.0] * n
    below = [i for i, payout in enumerate(payouts) if payout <= target]
    above = [i for i, payout in enumerate(payouts) if payout >= target]
    extra = 1_000_000.0
    if not below and not above:
        return weights
    if not below:
        high = min(above, key=lambda i: payouts[i])
        weights[high] += extra
        return weights
    if not above:
        low = max(below, key=lambda i: payouts[i])
        weights[low] += extra
        return weights
    lo_i = max(below, key=lambda i: payouts[i])
    hi_i = min(above, key=lambda i: payouts[i])
    lo, hi = payouts[lo_i], payouts[hi_i]
    if hi - lo < 1e-9:
        weights[lo_i] += extra
        return weights
    weights[lo_i] += extra * (hi - target)
    weights[hi_i] += extra * (target - lo)
    return weights


def lut_stats(rows: list[tuple[int, int, int]]) -> dict[str, float]:
    total_w = sum(weight for _, weight, _ in rows)
    expected = sum(weight * (cents / 100.0) for _, weight, cents in rows) / total_w
    mass = {"dead": 0.0, "recoup": 0.0, "wincap": 0.0}
    hit = 0.0
    for _, weight, cents in rows:
        mass[classify(cents)] += weight / total_w
        if cents > 0:
            hit += weight / total_w
    return {
        "rtp": expected / BUY_BONUS_COST,
        "expected": expected,
        "dead_mass": mass["dead"],
        "recoup_mass": mass["recoup"] + mass["wincap"],
        "wincap_mass": mass["wincap"],
        "hit_rate": hit,
        "books": float(len(rows)),
        "total_weight": float(total_w),
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
    if abs(stats["dead_mass"] - DEAD_MASS) > 0.01:
        raise ValueError(f"dead mass {stats['dead_mass']:.4f} is not 75%")
    if abs(stats["recoup_mass"] - RECOUP_MASS) > 0.01:
        raise ValueError(f"recoup mass {stats['recoup_mass']:.4f} is not 25%")
    if stats["hit_rate"] < 1 / 50:
        raise ValueError(f"non-zero hit rate {stats['hit_rate']:.4f} is worse than 1/50")
    return stats


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    publish = os.path.join(here, "library", "publish_files")
    stats = weight_bonus_lookup(publish)
    print("bonus LUT", stats)
