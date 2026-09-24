"""Repair 4-scatter extras where a wild + following symbols should have paid.

Existing books sometimes reveal a left-to-right wild ways hit and then skip
winInfo / holdRespin, so the extra looks winning but locks nothing.
"""

from __future__ import annotations

from base_feature import _set_cell, visible_grid, ways_detail


def _cents(pay: float) -> int:
    return int(round(pay * 100))


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
        name = cell.get("name") if isinstance(cell, dict) else str(cell)
        if name == "S" or name == "W":
            continue
        _set_cell(col, target, "W")
        changed = True
    return changed


def patch_book(book: dict) -> bool:
    events = list(book.get("events") or [])
    if not any(event.get("type") == "placeWild" for event in events):
        return False
    wilds = _sticky_wilds(events)
    changed = False
    inserts: list[tuple[int, list[dict]]] = []
    for index, event in enumerate(events):
        if event.get("type") != "reveal" or event.get("gameType") != "freegame":
            continue
        if wilds and _stamp_wilds(event.get("board") or [], wilds):
            changed = True
        names = visible_grid(event.get("board") or [])
        pay, wins = ways_detail(names)
        if pay <= 0 or not wins:
            continue
        end = _next_boundary(events, index)
        if _has_win_info(events, index, end):
            continue
        extra = [
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
                    { (pos["reel"], pos["row"]): pos for win in wins for pos in win["positions"] }.values(),
                    key=lambda pos: (pos["reel"], pos["row"]),
                ),
                "continuing": True,
            },
            {"type": "setWin", "amount": _cents(pay), "winLevel": 1},
        ]
        inserts.append((end, extra))
        changed = True
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
    book["payoutMultiplier"] = running
    book["freeGameWins"] = running / 100.0
    return True
