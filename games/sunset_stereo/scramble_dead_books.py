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
    filler_column_reels,
    is_stacked_column_board,
    paint_hit_fillers,
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


def _apply_board(event: dict, names: list[list[str]], rng) -> None:
    board = event["board"]
    keep = {name for col in names for name in col if name in PAYING}
    tops, bottoms = paint_mixed_pads(rng, names, forbidden=keep)
    new_board = []
    for reel, col in enumerate(board):
        rebuilt = [_cell_json(tops[reel], col[0])]
        for row, name in enumerate(names[reel]):
            rebuilt.append(_cell_json(name, col[1 + row] if len(col) > 1 + row else None))
        rebuilt.append(_cell_json(bottoms[reel], col[-1]))
        new_board.append(rebuilt)
    event["board"] = new_board
    event["paddingPositions"] = [rng.randrange(256) for _ in range(6)]


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
    _apply_board(event, names, rng)
    return True


def _wininfo_after(events: list, index: int) -> dict | None:
    for nxt in events[index + 1 :]:
        if nxt.get("type") == "reveal":
            return None
        if nxt.get("type") == "winInfo":
            return nxt
    return None


def _occupied_from_wininfo(win: dict, visible: list[list[str]]) -> dict[tuple[int, int], str]:
    occupied = _locked_from_visible(visible)
    for item in win.get("wins") or []:
        for pos in item.get("positions") or []:
            reel = int(pos["reel"])
            row = int(pos["row"]) - 1
            if 0 <= reel < 6 and 0 <= row < 4:
                occupied[(reel, row)] = visible[reel][row]
    return occupied


def _rewrite_hit_reveal(event: dict, win: dict, book_id: int, salt: int) -> bool:
    board = event.get("board")
    if not board:
        return False
    visible = _visible(board)
    occupied = _occupied_from_wininfo(win, visible)
    before = visible_ways_win(visible)
    rng = random.Random((int(book_id) + 1) * 9001 + salt * 31)
    names = paint_hit_fillers(occupied, rng)
    if visible_ways_win(names) != before:
        return False
    if names == visible and not filler_column_reels(visible, occupied):
        return False
    _apply_board(event, names, rng)
    return True


def scramble_book(book: dict) -> bool:
    events = book.get("events") or []
    changed = False
    reveal_i = 0
    for index, event in enumerate(events):
        if event.get("type") != "reveal":
            continue
        visible = _visible(event.get("board") or [])
        win = _wininfo_after(events, index)
        if win:
            changed = _rewrite_hit_reveal(event, win, int(book.get("id") or 0), reveal_i) or changed
        elif _looks_column_dead(visible):
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


DEMO = os.path.join(ROOT, "apps", "sunset-stereo", "src", "rgs", "demoBooks.json")


def scramble_demo() -> int:
    if not os.path.isfile(DEMO):
        return 0
    with open(DEMO, encoding="utf-8") as handle:
        pack = json.load(handle)
    changed = 0
    for key, books in pack.items():
        if not isinstance(books, list):
            continue
        for book in books:
            if scramble_book(book):
                changed += 1
    with open(DEMO, "w", encoding="utf-8") as handle:
        json.dump(pack, handle, separators=(",", ":"))
        handle.write("\n")
    print(f"demoBooks: {changed} books rewritten")
    return changed


def main() -> None:
    args = sys.argv[1:]
    if args == ["demo"] or "demo" in args:
        scramble_demo()
        args = [item for item in args if item != "demo"]
        if not args:
            return
    modes = args or list(MODES)
    for mode in modes:
        print(f"patching {mode}", flush=True)
        total, changed = patch_mode(mode)
        print(f"{mode}: {changed}/{total} books rewritten", flush=True)


if __name__ == "__main__":
    main()
