"""Generate 6-reel Sunset Stereo strips for the 4-row ways board.

Scatter only on reels 2-5 (1-indexed). Isolated so a 4-row window never
shows two suns on the same reel. No wilds.
"""

from __future__ import annotations

import os
import random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REELS_DIR = os.path.join(HERE, "reels")

PAYING = ["H1", "H2", "H3", "H4", "H5", "L1", "L2", "L3", "L4", "L5"]

# Index 0 = reel 1. Scatter weight is 0 on the first and last reels.
BASE_WEIGHTS = [
    {"H1": 6, "H2": 8, "H3": 10, "H4": 12, "H5": 12, "L1": 16, "L2": 18, "L3": 18, "L4": 20, "L5": 22, "S": 0},
    {"H1": 6, "H2": 9, "H3": 11, "H4": 12, "H5": 12, "L1": 15, "L2": 16, "L3": 17, "L4": 18, "L5": 19, "S": 3},
    {"H1": 6, "H2": 9, "H3": 11, "H4": 12, "H5": 12, "L1": 15, "L2": 16, "L3": 16, "L4": 17, "L5": 18, "S": 3},
    {"H1": 6, "H2": 9, "H3": 11, "H4": 12, "H5": 12, "L1": 15, "L2": 16, "L3": 16, "L4": 17, "L5": 18, "S": 3},
    {"H1": 6, "H2": 9, "H3": 11, "H4": 12, "H5": 12, "L1": 15, "L2": 16, "L3": 17, "L4": 18, "L5": 19, "S": 3},
    {"H1": 6, "H2": 8, "H3": 10, "H4": 12, "H5": 12, "L1": 16, "L2": 18, "L3": 18, "L4": 20, "L5": 22, "S": 0},
]


def _pick(weights: dict[str, int], rng: random.Random) -> str:
    symbols, values = zip(*weights.items())
    return rng.choices(symbols, weights=values, k=1)[0]


def _can_place_scatter(strip: list[str], min_gap: int = 4) -> bool:
    if not strip:
        return True
    last_s = None
    for i, sym in enumerate(strip):
        if sym == "S":
            last_s = i
    if last_s is None:
        return True
    return (len(strip) - last_s) >= min_gap


def build_strip(weights: dict[str, int], length: int, rng: random.Random) -> list[str]:
    paying_weights = {k: v for k, v in weights.items() if k != "S"}
    scatter_weight = weights.get("S", 0)
    total = sum(weights.values()) or 1
    strip: list[str] = []
    while len(strip) < length:
        if scatter_weight and _can_place_scatter(strip) and rng.random() < (scatter_weight / total):
            strip.append("S")
        else:
            strip.append(_pick(paying_weights, rng))

    if scatter_weight:
        scatter_count = strip.count("S")
        if scatter_count < 3:
            for i in range(2, length - 2, 5):
                window = strip[max(0, i - 3) : i + 4]
                if "S" not in window:
                    strip[i] = "S"
                    scatter_count += 1
                if scatter_count >= 3:
                    break

    for i in range(2, length):
        if strip[i] == strip[i - 1] == strip[i - 2] and strip[i] in PAYING:
            strip[i] = _pick(paying_weights, rng)

    assert "W" not in strip
    return strip


def write_csv(name: str, strips: list[list[str]]) -> None:
    path = os.path.join(REELS_DIR, name)
    rows = zip(*strips)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(",".join(row) + "\n")
    counts = [Counter(strip) for strip in strips]
    print(f"wrote {path} ({len(strips[0])} stops, {len(strips)} reels)")
    for idx, count in enumerate(counts):
        print(f"  reel {idx}: {dict(count)}")


def main() -> None:
    os.makedirs(REELS_DIR, exist_ok=True)
    rng = random.Random(19890707)
    strips = [build_strip(w, 196, rng) for w in BASE_WEIGHTS]
    write_csv("BR0.csv", strips)


if __name__ == "__main__":
    main()
