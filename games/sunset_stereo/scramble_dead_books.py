"""Rewrite columnar zero-pay reveals into mixed no-win boards.

Keeps book ids, payoutMultiplier, LUT rows, scatters and wilds in place.
Run after changing paint_mixed_dead so published books match the generator.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
from io import TextIOWrapper

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from game_config import BONUS_PAYING  # noqa: E402
from ways_paint import (  # noqa: E402
    is_stacked_column_board,
    paint_mixed_dead,
    paint_mixed_pads,
    visible_ways_win,
)

PAYING = set(BONUS_PAYING)
SRC = os.path.join(HERE, "library", "publish_files")
DST = os.path.join(ROOT, "publish", "sunset_stereo")
MODES = ("base", "scatter", "bonus", "wildbonus")


def _name(cell) -> str:
    return cell["name"] if isinstance(cell, dict) else str(cell)


def _visible(board: list) -> list[list[str]]:
    return [[_name(cell) for cell in col[1:-1]] for col in board]


def _cell_json(name: str, original=None):
    if original is not None and _name(original) == name:
        return original
    if name == "S":
        return {"name": "S", "scatter": True}
    if name == "W":
        return {"name": "W", "wild": True}
    return {"name": name}


def _locked_from_visible(visible: list[list[str]]) -> dict[tuple[int, int], str]:
    locked: dict[tuple[int, int], str] = {}
    for reel, col in enumerate(visible):
        for row, name in enumerate(col):
            if name in {"S", "W"}:
                locked[(reel, row)] = name
    return locked


def _looks_column_dead(visible: list[list[str]]) -> bool:
    return is_stacked_column_board(visible)


def _rewrite_reveal(event: dict, book_id: int, salt: int) -> bool:
    board = event.get("board")
    if not board:
        return False
    visible = _visible(board)
    locked = _locked_from_visible(visible)
    rng = random.Random((int(book_id) + 1) * 10007 + salt * 17)
    names = paint_mixed_dead(rng, locked)
    if visible_ways_win(names) != 0:
        return False
    tops, bottoms = paint_mixed_pads(rng, names)
    new_board = []
    for reel, col in enumerate(board):
        rebuilt = [_cell_json(tops[reel], col[0])]
        for row, name in enumerate(names[reel]):
            rebuilt.append(_cell_json(name, col[1 + row] if len(col) > 1 + row else None))
        rebuilt.append(_cell_json(bottoms[reel], col[-1]))
        new_board.append(rebuilt)
    event["board"] = new_board
    event["paddingPositions"] = [rng.randrange(256) for _ in range(6)]
    return True


def _reveal_pays(events: list, index: int) -> bool:
    for nxt in events[index + 1 :]:
        if nxt.get("type") == "reveal":
            return False
        if nxt.get("type") == "winInfo":
            return True
    return False


def scramble_book(book: dict) -> bool:
    events = book.get("events") or []
    changed = False
    payout = int(book.get("payoutMultiplier") or 0)
    reveal_i = 0
    for index, event in enumerate(events):
        if event.get("type") != "reveal":
            continue
        visible = _visible(event.get("board") or [])
        rewrite = payout == 0 or (not _reveal_pays(events, index) and _looks_column_dead(visible))
        if rewrite:
            changed = _rewrite_reveal(event, int(book.get("id") or 0), reveal_i) or changed
        reveal_i += 1
    return changed


def patch_mode(mode: str) -> tuple[int, int]:
    src = os.path.join(SRC, f"books_{mode}.jsonl.zst")
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    import zstandard as zst

    tmp = src + ".tmp"
    changed = 0
    total = 0
    compressor = zst.ZstdCompressor()
    with open(src, "rb") as handle, open(tmp, "wb") as out:
        with zst.ZstdDecompressor().stream_reader(handle) as reader:
            with compressor.stream_writer(out, closefd=False) as writer:
                for line in TextIOWrapper(reader, encoding="utf-8"):
                    if not line.strip():
                        continue
                    total += 1
                    book = json.loads(line)
                    if scramble_book(book):
                        changed += 1
                        blob = json.dumps(book, ensure_ascii=True) + "\n"
                    else:
                        blob = line if line.endswith("\n") else line + "\n"
                    writer.write(blob.encode("utf-8"))
                    if total % 100000 == 0:
                        print(f"  {mode} scanned {total} changed {changed}", flush=True)
    os.replace(tmp, src)
    dest = os.path.join(DST, f"books_{mode}.jsonl.zst")
    os.makedirs(DST, exist_ok=True)
    shutil.copy2(src, dest)
    return total, changed


def main() -> None:
    modes = sys.argv[1:] or list(MODES)
    for mode in modes:
        print(f"patching {mode}", flush=True)
        total, changed = patch_mode(mode)
        print(f"{mode}: {changed}/{total} books rewritten", flush=True)


if __name__ == "__main__":
    main()
