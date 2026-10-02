"""Regenerate published natural 4-scatter bonuses and reconcile their LUTs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from io import TextIOWrapper

import zstandard as zst

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)

from base_feature import visible_grid  # noqa: E402
from bonus_freq import reweight_publish_dir  # noqa: E402
from game_config import GameConfig  # noqa: E402
from gamestate import GameState  # noqa: E402

MODES = ("base", "scatter")


def validate_four_scatter(book: dict) -> None:
    events = book["events"]
    trigger = next(event for event in events if event["type"] == "freeSpinTrigger")
    if len(trigger["positions"]) != 4:
        raise ValueError(f"book {book['id']} has no 4-scatter trigger")
    extra = 0
    wild = None
    places = 0
    for event in events:
        kind = event["type"]
        if kind == "updateFreeSpin":
            extra += 1
            wild = None
        elif kind == "placeWild":
            if wild is not None:
                raise ValueError(f"book {book['id']} extra {extra} placed multiple wilds")
            wild = (int(event["reel"]), int(event["row"]) - 1)
            places += 1
        elif kind == "reveal" and event.get("gameType") == "freegame":
            names = visible_grid(event["board"])
            positions = {
                (reel, row)
                for reel, col in enumerate(names)
                for row, name in enumerate(col)
                if name == "W"
            }
            if wild is None or positions != {wild}:
                raise ValueError(f"book {book['id']} extra {extra} has {positions}, expected {wild}")
    if not extra or places != extra:
        raise ValueError(f"book {book['id']} has {places} wilds for {extra} extra plays")
    final = next(event for event in events if event["type"] == "finalWin")
    if int(final["amount"]) != int(book["payoutMultiplier"]):
        raise ValueError(f"book {book['id']} finalWin does not match payoutMultiplier")


def regenerate(book: dict, state: GameState, mode: str) -> dict:
    state.betmode = mode
    state.criteria = book["criteria"]
    state.run_spin(int(book["id"]))
    replacement = state.book.to_json()
    replacement["id"] = book["id"]
    replacement["criteria"] = book["criteria"]
    validate_four_scatter(replacement)
    return replacement


def repair_mode(publish_dir: str, mode: str) -> dict[str, int]:
    books_path = os.path.join(publish_dir, f"books_{mode}.jsonl.zst")
    lut_path = os.path.join(publish_dir, f"lookUpTable_{mode}_0.csv")
    replacements: dict[int, int] = {}
    stats = {"scanned": 0, "repaired": 0, "changed_payouts": 0}
    state = GameState(GameConfig())
    tmp = books_path + ".fourtmp"
    with open(books_path, "rb") as source, open(tmp, "wb") as output:
        with zst.ZstdDecompressor().stream_reader(source) as reader:
            with zst.ZstdCompressor(level=3).stream_writer(output, closefd=False) as writer:
                for raw in TextIOWrapper(reader, encoding="utf-8"):
                    if not raw.strip():
                        continue
                    book = json.loads(raw)
                    stats["scanned"] += 1
                    if book["criteria"] in {"freegame4", "wincap"}:
                        fixed = regenerate(book, state, mode)
                        book_id = int(book["id"])
                        payout = int(fixed["payoutMultiplier"])
                        replacements[book_id] = payout
                        stats["repaired"] += 1
                        stats["changed_payouts"] += payout != int(book["payoutMultiplier"])
                        raw = json.dumps(fixed, separators=(",", ":")) + "\n"
                    writer.write(raw.encode("utf-8"))
                    if stats["scanned"] % 100000 == 0:
                        print(f"{mode}: {stats['scanned']} scanned, {stats['repaired']} repaired", flush=True)
    if not replacements:
        raise ValueError(f"{mode} has no natural 4-scatter books")
    rows = []
    with open(lut_path, newline="", encoding="utf-8") as handle:
        for book_id, weight, payout in csv.reader(handle):
            ident = int(book_id)
            rows.append((ident, int(weight), replacements.get(ident, int(payout))))
    if not set(replacements).issubset({book_id for book_id, _, _ in rows}):
        raise ValueError(f"{mode} LUT is missing regenerated books")
    os.replace(tmp, books_path)
    with open(lut_path, "w", encoding="utf-8", newline="\n") as handle:
        for book_id, weight, payout in rows:
            handle.write(f"{book_id},{weight},{payout}\n")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    args = parser.parse_args()
    stats = {mode: repair_mode(args.dir, mode) for mode in args.modes}
    weighted = reweight_publish_dir(args.dir, args.modes)
    print(json.dumps({"books": stats, "weights": weighted}, indent=2, default=str))


if __name__ == "__main__":
    main()
