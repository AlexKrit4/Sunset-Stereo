"""Delay the first paying bonus extra play in ~90% of books.

Keeps payoutMultiplier / LUT rows. The original paying extra is moved later
and split into 2–3 hold-respins that grow into the same winInfo.
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

from scramble_dead_books import _apply_board, _occupied_from_wininfo, _visible  # noqa: E402
from ways_paint import (  # noqa: E402
    delay_opening_win,
    growing_hold_stages,
    opening_respin_count,
    paint_hit_fillers,
    visible_ways_win,
)

SRC = os.path.join(HERE, "library", "publish_files")
DST = os.path.join(ROOT, "publish", "sunset_stereo")
DEMO = os.path.join(ROOT, "apps", "sunset-stereo", "src", "rgs", "demoBooks.json")
MODES = ("base", "scatter", "bonus", "wildbonus")
TAIL = {"freeSpinEnd", "finalWin"}


def _reindex(events: list[dict]) -> None:
    for index, event in enumerate(events):
        event["index"] = index


def _chunk_bounds(events: list[dict]) -> list[tuple[int, int]]:
    starts = [index for index, event in enumerate(events) if event.get("type") == "updateFreeSpin"]
    bounds = []
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else len(events)
        bounds.append((start, end))
    return bounds


def _has_win(body: list[dict]) -> bool:
    return any(event.get("type") == "winInfo" for event in body)


def _has_wincap(body: list[dict]) -> bool:
    return any(event.get("type") == "wincap" for event in body)


def _split_tail(body: list[dict]) -> tuple[list[dict], list[dict]]:
    core = list(body)
    tail: list[dict] = []
    while core and core[-1].get("type") in TAIL:
        tail.insert(0, core.pop())
    return core, tail


def _hold_event(occupied: dict) -> dict:
    padded = [{"reel": reel, "row": row + 1} for reel, row in sorted(occupied)]
    return {"type": "holdRespin", "positions": padded, "continuing": True}


def _stage_reveal(template: dict, occupied: dict, book_id: int, salt: int) -> dict:
    nxt = deepcopy(template)
    names = None
    rng_used = None
    for attempt in range(16):
        rng = random.Random((int(book_id) + 1) * 11003 + salt * 47 + attempt * 7919)
        candidate = paint_hit_fillers(occupied, rng)
        if visible_ways_win(candidate) <= 0:
            continue
        names = candidate
        rng_used = rng
        break
    if names is None:
        rng_used = random.Random((int(book_id) + 1) * 11003 + salt)
        names = _visible(template.get("board") or [])
        for (reel, row), name in occupied.items():
            if 0 <= reel < 6 and 0 <= row < 4:
                names[reel][row] = name
    _apply_board(nxt, names, rng_used)
    nxt["type"] = "reveal"
    return nxt


def _restage_body(body: list[dict], book_id: int, n_respins: int) -> list[dict] | None:
    types = [event.get("type") for event in body]
    if "winInfo" not in types:
        return None
    win = next(event for event in body if event.get("type") == "winInfo")
    reveals = [event for event in body if event.get("type") == "reveal"]
    if not reveals:
        return None
    last = reveals[-1]
    visible = _visible(last.get("board") or [])
    occupied = _occupied_from_wininfo(win, visible)
    if len(occupied) < 3:
        return None
    stages = growing_hold_stages(occupied, n_respins=n_respins)
    prefix: list[dict] = []
    suffix: list[dict] = []
    seen_reveal = False
    for event in body:
        kind = event.get("type")
        if kind in {"reveal", "holdRespin"}:
            seen_reveal = True
            continue
        if not seen_reveal:
            prefix.append(event)
        else:
            suffix.append(event)
    middle: list[dict] = []
    for index, stage in enumerate(stages):
        last_stage = index == len(stages) - 1
        if last_stage:
            middle.append(deepcopy(last))
        else:
            middle.append(_stage_reveal(last, stage, book_id, index + 1))
        if not last_stage:
            middle.append(_hold_event(stage))
    return prefix + middle + suffix


def _rebuild_totals(events: list[dict]) -> None:
    running = 0
    in_bonus = False
    pending_spin = 0
    for event in events:
        kind = event.get("type")
        if kind == "updateFreeSpin":
            in_bonus = True
        if kind == "setTotalWin" and not in_bonus:
            running = int(event.get("amount") or 0)
            continue
        if kind == "winInfo" and in_bonus:
            pending_spin = int(event.get("totalWin") or 0)
        if kind == "setWin" and in_bonus:
            event["amount"] = pending_spin
        if kind == "setTotalWin" and in_bonus:
            running += pending_spin
            event["amount"] = running
            pending_spin = 0


def transform_book(book: dict) -> bool:
    events = book.get("events") or []
    bounds = _chunk_bounds(events)
    if not bounds:
        return False
    changed = False
    book_id = int(book.get("id") or 0)
    bodies = []
    tails: list[dict] = []
    for start, end in bounds:
        core, tail = _split_tail(events[start + 1 : end])
        bodies.append(core)
        tails.extend(tail)

    n_respins = opening_respin_count(book_id)
    pay_at = next((index for index, body in enumerate(bodies) if _has_win(body)), None)
    if pay_at is not None:
        restaged = _restage_body(bodies[pay_at], book_id, n_respins)
        if restaged is not None:
            bodies[pay_at] = restaged
            changed = True
        if (
            pay_at == 0
            and delay_opening_win(book_id)
            and not _has_wincap(bodies[0])
        ):
            later = [
                index
                for index, body in enumerate(bodies[1:], start=1)
                if not _has_win(body) and not _has_wincap(body)
            ]
            if later:
                swap = later[0]
                bodies[0], bodies[swap] = bodies[swap], bodies[0]
                changed = True

    if not changed:
        return False

    rebuilt = events[: bounds[0][0]]
    for offset, (start, _end) in enumerate(bounds):
        rebuilt.append(events[start])
        rebuilt.extend(bodies[offset])
    rebuilt.extend(tails)
    rebuilt.extend(events[bounds[-1][1] :])
    _rebuild_totals(rebuilt)
    _reindex(rebuilt)
    book["events"] = rebuilt
    return True


def patch_mode(mode: str) -> tuple[int, int]:
    src = os.path.join(SRC, f"books_{mode}.jsonl.zst")
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    import zstandard as zst

    tmp = src + ".opentmp"
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
                    if transform_book(book):
                        changed += 1
                        blob = json.dumps(book, ensure_ascii=True) + "\n"
                    else:
                        blob = line if line.endswith("\n") else line + "\n"
                    writer.write(blob.encode("utf-8"))
                    if total % 50000 == 0:
                        print(f"  {mode} scanned {total} patched {changed}", flush=True)
    os.replace(tmp, src)
    os.makedirs(DST, exist_ok=True)
    shutil.copy2(src, os.path.join(DST, f"books_{mode}.jsonl.zst"))
    return total, changed


def patch_demo(keys: tuple[str, ...] | None = None) -> None:
    with open(DEMO, encoding="utf-8") as handle:
        pack = json.load(handle)
    changed = 0
    for key in keys or ("books", "scatterBooks", "bonusBooks", "wildBonusBooks"):
        for book in pack.get(key) or []:
            if transform_book(book):
                changed += 1
    with open(DEMO, "w", encoding="utf-8") as handle:
        json.dump(pack, handle, separators=(",", ":"))
        handle.write("\n")
    print(f"demo patched {changed} books")


def main() -> None:
    args = sys.argv[1:] or ["demo", *MODES]
    if "demo" in args:
        patch_demo(("books", "scatterBooks"))
    for mode in MODES:
        if mode in args:
            total, changed = patch_mode(mode)
            print(f"{mode}: patched {changed}/{total}", flush=True)


if __name__ == "__main__":
    main()
