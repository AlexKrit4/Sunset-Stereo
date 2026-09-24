"""Repair 4-scatter extras where a wild + following symbols should have paid.

The camera wild is sticky. If the first extra (or a board that already has W)
shows a left-to-right ways hit and there is no winInfo, lock that line.
Later extras that only look winning because the overlay wild sits on a dead
board are repainted dead with the wild locked, so we do not invent ten pays.
"""

from __future__ import annotations

import random

from base_feature import _set_cell, visible_grid, ways_detail
from ways_paint import paint_mixed_dead, paint_mixed_pads, visible_ways_win


def _cents(pay: float) -> int:
    return int(round(pay * 100))


def _cell_name(cell) -> str:
    if isinstance(cell, dict):
        return str(cell.get("name") or "")
    return str(cell)


def _next_boundary(events: list, start: int) -> int:
    for index in range(start + 1, len(events)):
        kind = events[index].get("type")
        if kind in {"reveal", "updateFreeSpin", "freeSpinEnd", "finalWin"}:
            return index
    return len(events)


def _has_win_info(events: list, start: int, end: int) -> bool:
    return any(event.get("type") == "winInfo" for event in events[start + 1 : end])


def _sticky_wilds(events: list) -> list[tuple[int, int]]:
    seen: list[tuple[int, int]] = []
    for event in events:
        if event.get("type") != "placeWild":
            continue
        cell = (int(event["reel"]), int(event["row"]))
        if cell not in seen:
            seen.append(cell)
    return seen


def _visible_already_has_wild(names: list[list[str]], wilds: list[tuple[int, int]]) -> bool:
    if any(name == "W" for col in names for name in col):
        return True
    for reel, padded_row in wilds:
        row = padded_row - 1
        if 0 <= reel < len(names) and 0 <= row < len(names[reel]) and names[reel][row] == "W":
            return True
    return False


def _stamp_wilds(board: list, wilds: list[tuple[int, int]]) -> bool:
    """Write the camera wild onto the padded/visible reveal board."""
    changed = False
    for reel, padded_row in wilds:
        if reel < 0 or reel >= len(board):
            continue
        col = board[reel]
        padded = len(col) >= 6
        target = padded_row if padded else padded_row - 1
        if target < 0 or target >= len(col):
            continue
        cell = col[target]
        name = _cell_name(cell)
        if name == "S" or name == "W":
            continue
        _set_cell(col, target, "W")
        changed = True
    return changed


def _locked_from_visible(names: list[list[str]]) -> dict[tuple[int, int], str]:
    locked: dict[tuple[int, int], str] = {}
    for reel, col in enumerate(names):
        for row, name in enumerate(col):
            if name in {"S", "W"}:
                locked[(reel, row)] = name
    return locked


def _apply_visible(event: dict, names: list[list[str]], rng) -> None:
    board = event["board"]
    keep = {name for col in names for name in col if name not in {"S", "W"}}
    tops, bottoms = paint_mixed_pads(rng, names, forbidden=keep)
    new_board = []
    for reel, col in enumerate(board):
        padded = len(col) >= 6
        if not padded:
            new_board.append([{"name": name, **({"wild": True} if name == "W" else {})} for name in names[reel]])
            continue
        rebuilt = [{"name": tops[reel]}]
        for name in names[reel]:
            payload = {"name": name}
            if name == "W":
                payload["wild"] = True
            if name == "S":
                payload["scatter"] = True
            rebuilt.append(payload)
        rebuilt.append({"name": bottoms[reel]})
        new_board.append(rebuilt)
    event["board"] = new_board


def _repaint_dead(event: dict, book_id: int, salt: int) -> bool:
    names = visible_grid(event.get("board") or [])
    locked = _locked_from_visible(names)
    rng = random.Random((int(book_id) + 1) * 10007 + salt * 17)
    painted = paint_mixed_dead(rng, locked)
    if visible_ways_win(painted) != 0:
        return False
    _apply_visible(event, painted, rng)
    return True


def _win_events(pay: float, wins: list[dict]) -> list[dict]:
    return [
        {
            "type": "winInfo",
            "totalWin": _cents(pay),
            "wins": [
                {
                    **win,
                    "win": _cents(win["win"]),
                    "meta": {
                        **win["meta"],
                        "winWithoutMult": _cents(win["meta"]["winWithoutMult"]),
                    },
                }
                for win in wins
            ],
        },
        {
            "type": "holdRespin",
            "positions": sorted(
                {(pos["reel"], pos["row"]): pos for win in wins for pos in win["positions"]}.values(),
                key=lambda pos: (pos["reel"], pos["row"]),
            ),
            "continuing": True,
        },
        {"type": "setWin", "amount": _cents(pay), "winLevel": 1},
    ]


def patch_book(book: dict) -> bool:
    events = list(book.get("events") or [])
    if not any(event.get("type") == "placeWild" for event in events):
        return False
    original_pay = int(book.get("payoutMultiplier") or 0)
    wilds = _sticky_wilds(events)
    changed = False
    inserts: list[tuple[int, list[dict]]] = []
    first_extra = True
    salt = 0
    for index, event in enumerate(events):
        if event.get("type") != "reveal" or event.get("gameType") != "freegame":
            continue
        names_before = visible_grid(event.get("board") or [])
        pay_before, wins_before = ways_detail(names_before)
        already_wild = _visible_already_has_wild(names_before, wilds)
        if wilds and _stamp_wilds(event.get("board") or [], wilds):
            changed = True
        names = visible_grid(event.get("board") or [])
        pay, wins = ways_detail(names)
        end = _next_boundary(events, index)
        has_win = _has_win_info(events, index, end)
        modest = pay > 0 and pay <= 5.0
        if modest and wins and not has_win and (already_wild or pay_before > 0 or first_extra):
            inserts.append((end, _win_events(pay, wins)))
            changed = True
        elif pay > 0 and not has_win:
            salt += 1
            if _repaint_dead(event, int(book.get("id") or 0), salt):
                changed = True
        first_extra = False
    if not changed:
        return False
    delta = 0
    for at, extra in inserts:
        at += delta
        events[at:at] = extra
        delta += len(extra)
    running = 0
    for event in events:
        if event.get("type") == "setWin":
            running += int(event.get("amount") or 0)
        if event.get("type") == "setTotalWin":
            event["amount"] = running
        if event.get("type") == "finalWin":
            event["amount"] = running
    for index, event in enumerate(events):
        event["index"] = index
    book["events"] = events
    if inserts:
        book["payoutMultiplier"] = running
        book["freeGameWins"] = running / 100.0
    else:
        book["payoutMultiplier"] = original_pay
    return True
