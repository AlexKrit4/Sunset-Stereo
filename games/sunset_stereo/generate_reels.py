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

# Extra-play strips: no scatters, slightly richer highs so held ways can grow.
FS_WEIGHTS = [
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "H5": 13, "L1": 14, "L2": 14, "L3": 14, "L4": 14, "L5": 15, "S": 0},
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "H5": 13, "L1": 14, "L2": 14, "L3": 14, "L4": 14, "L5": 15, "S": 0},
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "H5": 13, "L1": 14, "L2": 14, "L3": 14, "L4": 14, "L5": 15, "S": 0},
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "H5": 13, "L1": 14, "L2": 14, "L3": 14, "L4": 14, "L5": 15, "S": 0},
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "H5": 13, "L1": 14, "L2": 14, "L3": 14, "L4": 14, "L5": 15, "S": 0},
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "H5": 13, "L1": 14, "L2": 14, "L3": 14, "L4": 14, "L5": 15, "S": 0},
]

# Buy-bonus extra-play strips. Same 6×4 ways, no scatters. Bias only the
# fill mix so dead/recoup/wincap quotas finish; reelstops stay random.
def _uniform(weights: dict[str, int]) -> list[dict[str, int]]:
    return [dict(weights) for _ in range(6)]


# Adjacent reels barely share symbols, so 4+ ways (which explode on a 4-row
# grid) almost never land. Dead books stay under the 95× buy without cloning boards.
DEAD_WEIGHTS = [
    {"L1": 48, "L2": 8, "H5": 3, "H4": 2, "H3": 1, "H2": 1, "H1": 1, "L3": 2, "L4": 2, "L5": 2, "S": 0},
    {"L3": 48, "L4": 8, "H5": 3, "H4": 2, "H3": 1, "H2": 1, "H1": 1, "L1": 2, "L2": 2, "L5": 2, "S": 0},
    {"L5": 48, "H5": 8, "H4": 4, "H3": 2, "H2": 1, "H1": 1, "L1": 2, "L2": 2, "L3": 2, "L4": 2, "S": 0},
    {"H4": 40, "L2": 12, "H3": 6, "H2": 2, "H1": 1, "H5": 3, "L1": 2, "L3": 4, "L4": 4, "L5": 4, "S": 0},
    {"H3": 40, "L1": 12, "H2": 6, "H1": 2, "H5": 3, "H4": 3, "L2": 4, "L3": 4, "L4": 4, "L5": 4, "S": 0},
    {"H2": 36, "L4": 14, "H1": 6, "H5": 4, "H4": 4, "H3": 4, "L1": 4, "L2": 4, "L3": 4, "L5": 4, "S": 0},
]
RECOUP_WEIGHTS = _uniform(
    {"H1": 22, "H2": 18, "H3": 14, "H4": 12, "H5": 10, "L1": 8, "L2": 7, "L3": 6, "L4": 5, "L5": 4, "S": 0}
)
WCAP_WEIGHTS = _uniform(
    {"H1": 48, "H2": 22, "H3": 10, "H4": 6, "H5": 4, "L1": 3, "L2": 3, "L3": 2, "L4": 1, "L5": 1, "S": 0}
)


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


def write_bonus_strips() -> None:
    """Extra-play strips for the 95× 3-scatter buy. Does not touch BR0/FR0."""
    os.makedirs(REELS_DIR, exist_ok=True)
    write_csv("FR_DEAD.csv", [build_strip(w, 196, random.Random(19890711 + i)) for i, w in enumerate(DEAD_WEIGHTS)])
    write_csv("FR_RECOUP.csv", [build_strip(w, 196, random.Random(19890721 + i)) for i, w in enumerate(RECOUP_WEIGHTS)])
    write_csv("FR_WCAP.csv", [build_strip(w, 196, random.Random(19890731 + i)) for i, w in enumerate(WCAP_WEIGHTS)])


def main() -> None:
    """Rewrite FR_DEAD / FR_RECOUP / FR_WCAP only. BR0 and FR0 are frozen
    to the published 1,000,000-book base pack and must not be regenerated.
    """
    os.makedirs(REELS_DIR, exist_ok=True)
    write_bonus_strips()


if __name__ == "__main__":
    main()
