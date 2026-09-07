"""Generate unique Sunset Stereo reelstrips.

Scatter symbols are isolated so a visible 3-row window never contains
two scatters on the same reel (required by force_special_board).
"""

from __future__ import annotations

import os
import random
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REELS_DIR = os.path.join(HERE, "reels")

PAYING = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "L5"]

# Per-reel relative weights. Wilds are scarcer on the first and last reels
# so 5-kind wilds stay rare; scatters sit on every reel for Golden Hour.
BASE_WEIGHTS = [
    {"H1": 5, "H2": 8, "H3": 11, "H4": 13, "L1": 16, "L2": 18, "L3": 18, "L4": 20, "L5": 22, "W": 2, "S": 2},
    {"H1": 6, "H2": 9, "H3": 11, "H4": 13, "L1": 15, "L2": 16, "L3": 17, "L4": 18, "L5": 19, "W": 5, "S": 2},
    {"H1": 6, "H2": 9, "H3": 12, "H4": 13, "L1": 15, "L2": 16, "L3": 16, "L4": 17, "L5": 18, "W": 6, "S": 2},
    {"H1": 6, "H2": 9, "H3": 11, "H4": 13, "L1": 15, "L2": 16, "L3": 17, "L4": 18, "L5": 19, "W": 5, "S": 2},
    {"H1": 5, "H2": 8, "H3": 11, "H4": 13, "L1": 16, "L2": 18, "L3": 18, "L4": 20, "L5": 22, "W": 2, "S": 2},
]

FREE_WEIGHTS = [
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "L1": 12, "L2": 12, "L3": 11, "L4": 10, "L5": 9, "W": 8, "S": 2},
    {"H1": 11, "H2": 12, "H3": 13, "H4": 12, "L1": 11, "L2": 11, "L3": 10, "L4": 9, "L5": 8, "W": 12, "S": 2},
    {"H1": 12, "H2": 13, "H3": 13, "H4": 12, "L1": 10, "L2": 10, "L3": 9, "L4": 8, "L5": 7, "W": 14, "S": 2},
    {"H1": 11, "H2": 12, "H3": 13, "H4": 12, "L1": 11, "L2": 11, "L3": 10, "L4": 9, "L5": 8, "W": 12, "S": 2},
    {"H1": 10, "H2": 12, "H3": 13, "H4": 13, "L1": 12, "L2": 12, "L3": 11, "L4": 10, "L5": 9, "W": 8, "S": 2},
]

WCAP_WEIGHTS = [
    {"H1": 16, "H2": 14, "H3": 12, "H4": 10, "L1": 6, "L2": 5, "L3": 4, "L4": 3, "L5": 2, "W": 16, "S": 2},
    {"H1": 16, "H2": 14, "H3": 11, "H4": 9, "L1": 5, "L2": 4, "L3": 3, "L4": 3, "L5": 2, "W": 20, "S": 2},
    {"H1": 18, "H2": 14, "H3": 10, "H4": 8, "L1": 4, "L2": 3, "L3": 3, "L4": 2, "L5": 2, "W": 22, "S": 2},
    {"H1": 16, "H2": 14, "H3": 11, "H4": 9, "L1": 5, "L2": 4, "L3": 3, "L4": 3, "L5": 2, "W": 20, "S": 2},
    {"H1": 16, "H2": 14, "H3": 12, "H4": 10, "L1": 6, "L2": 5, "L3": 4, "L4": 3, "L5": 2, "W": 16, "S": 2},
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


def build_strip(weights: dict[str, int], length: int, rng: random.Random, min_scatters: int = 3) -> list[str]:
    paying_weights = {k: v for k, v in weights.items() if k != "S"}
    strip: list[str] = []
    while len(strip) < length:
        if _can_place_scatter(strip) and rng.random() < (weights.get("S", 0) / sum(weights.values())):
            strip.append("S")
        else:
            strip.append(_pick(paying_weights, rng))

    # Guarantee isolated scatters exist so force_special_board can land them.
    scatter_count = strip.count("S")
    if scatter_count < min_scatters:
        for i in range(2, length - 2, 5):
            window = strip[max(0, i - 3) : i + 4]
            if "S" not in window:
                strip[i] = "S"
                scatter_count += 1
            if scatter_count >= min_scatters:
                break

    # Break accidental 3-in-a-row of the same low symbol to keep the board lively.
    for i in range(2, length):
        if strip[i] == strip[i - 1] == strip[i - 2] and strip[i] in PAYING:
            strip[i] = _pick(paying_weights, rng)

    return strip


def write_csv(name: str, strips: list[list[str]]) -> None:
    path = os.path.join(REELS_DIR, name)
    rows = zip(*strips)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(",".join(row) + "\n")
    counts = [Counter(strip) for strip in strips]
    print(f"wrote {path} ({len(strips[0])} stops)")
    for idx, count in enumerate(counts):
        print(f"  reel {idx}: {dict(count)}")


def write_frontend_reels(reels: dict[str, list[list[str]]]) -> None:
    frontend_dir = os.path.abspath(os.path.join(HERE, "..", "..", "frontend", "js"))
    os.makedirs(frontend_dir, exist_ok=True)
    path = os.path.join(frontend_dir, "reels.js")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("export const REELS = {\n")
        for name, strips in reels.items():
            handle.write(f"  {name}: [\n")
            for strip in strips:
                handle.write("    " + repr(strip) + ",\n")
            handle.write("  ],\n")
        handle.write("};\n")
    print(f"wrote {path}")


def main() -> None:
    os.makedirs(REELS_DIR, exist_ok=True)
    rng = random.Random(19890707)

    reels = {
        "BR0": [build_strip(w, 196, rng, min_scatters=4) for w in BASE_WEIGHTS],
        "FR0": [build_strip(w, 184, rng, min_scatters=4) for w in FREE_WEIGHTS],
        "WCAP": [build_strip(w, 112, rng, min_scatters=3) for w in WCAP_WEIGHTS],
    }
    write_csv("BR0.csv", reels["BR0"])
    write_csv("FR0.csv", reels["FR0"])
    write_csv("FRWCAP.csv", reels["WCAP"])
    write_frontend_reels(reels)


if __name__ == "__main__":
    main()
