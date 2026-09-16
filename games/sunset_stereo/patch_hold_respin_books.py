"""Insert missing hold-and-respin reveals into published books.

Keeps payoutMultiplier / LUT rows. A paying extra play always gets
holdRespin plus a follow-up reveal before winInfo.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
from copy import deepcopy
from io import TextIOWrapper

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from scramble_dead_books import (  # noqa: E402
    _apply_board,
    _locked_from_visible,
    _occupied_from_wininfo,
    _visible,
)
from ways_paint import paint_hit_fillers, visible_ways_win  # noqa: E402

SRC = os.path.join(HERE, "library", "publish_files")
DST = os.path.join(ROOT, "publish", "sunset_stereo")
MODES = ("base", "scatter", "bonus", "wildbonus")


def _reindex(events: list[dict]) -> None:
    for index, event in enumerate(events):
        event["index"] = index


def _win_in_chunk(events: list[dict]) -> dict | None:
    for event in events:
        if event.get("type") == "winInfo":
            return event
    return None


def _safe_respin_board(reveal: dict, occupied: dict, book_id: int, salt: int) -> dict:
    visible = _visible(reveal.get("board") or [])
    want = visible_ways_win(visible)
    names = None
    rng_used = None
    for attempt in range(16):
        rng = random.Random((int(book_id) + 1) * 11003 + salt * 47 + attempt * 7919)
        candidate = paint_hit_fillers(occupied, rng)
        if visible_ways_win(candidate) != want:
            continue
        names = candidate
        rng_used = rng
        break
    nxt = deepcopy(reveal)
    if names is None:
        rng_used = random.Random((int(book_id) + 1) * 11003 + salt)
        names = visible
    _apply_board(nxt, names, rng_used)
    nxt["type"] = "reveal"
    return nxt


def _hold_event(occupied: dict) -> dict:
    padded = [{"reel": reel, "row": row + 1} for reel, row in sorted(occupied)]
    return {"type": "holdRespin", "positions": padded, "continuing": True}


def _chunk_bounds(events: list[dict]) -> list[tuple[int, int]]:
    starts = [index for index, event in enumerate(events) if event.get("type") == "updateFreeSpin"]
    bounds = []
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else len(events)
        bounds.append((start, end))
    return bounds


def patch_book(book: dict) -> bool:
    events = book.get("events") or []
    changed = False
    inserted = 0
    for start, end in reversed(_chunk_bounds(events)):
        chunk = events[start:end]
        types = [event.get("type") for event in chunk]
        win = _win_in_chunk(chunk)
        if win is None:
            continue
        reveals = [index for index, kind in enumerate(types) if kind == "reveal"]
        if not reveals:
            continue
        holds = [index for index, kind in enumerate(types) if kind == "holdRespin"]
        first_reveal = chunk[reveals[0]]
        last_reveal = chunk[reveals[-1]]
        visible = _visible(last_reveal.get("board") or [])
        occupied = _occupied_from_wininfo(win, visible)
        if not occupied:
            occupied = _locked_from_visible(visible)
        book_id = int(book.get("id") or 0)
        if not holds:
            hold = _hold_event(occupied)
            nxt = _safe_respin_board(first_reveal, occupied, book_id, inserted + start)
            insert_at = start + reveals[0] + 1
            events[insert_at:insert_at] = [hold, nxt]
            changed = True
            inserted += 2
            continue
        last_hold = holds[-1]
        win_at = types.index("winInfo")
        if "reveal" not in types[last_hold + 1 : win_at]:
            nxt = _safe_respin_board(last_reveal, occupied, book_id, inserted + start + last_hold)
            events.insert(start + last_hold + 1, nxt)
            changed = True
            inserted += 1
    if changed:
        _reindex(events)
        book["events"] = events
    return changed


def patch_mode(mode: str) -> tuple[int, int]:
    src = os.path.join(SRC, f"books_{mode}.jsonl.zst")
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    import zstandard as zst

    tmp = src + ".holdtmp"
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
                    if patch_book(book):
                        changed += 1
                        blob = json.dumps(book, ensure_ascii=True) + "\n"
                    else:
                        blob = line if line.endswith("\n") else line + "\n"
                    writer.write(blob.encode("utf-8"))
                    if total % 50000 == 0:
                        print(f"  {mode} scanned {total} patched {changed}", flush=True)
    os.replace(tmp, src)
    dest = os.path.join(DST, f"books_{mode}.jsonl.zst")
    os.makedirs(DST, exist_ok=True)
    shutil.copy2(src, dest)
    return total, changed


def main() -> None:
    modes = sys.argv[1:] or list(MODES)
    for mode in modes:
        total, changed = patch_mode(mode)
        print(f"{mode}: patched {changed}/{total}", flush=True)


if __name__ == "__main__":
    main()
