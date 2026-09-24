"""4% base-spin feature on the 1× bet and 1.5× ante.

Stake books own the outcome: no client RNG. Feature books do not have to pay,
so the 4% rate is locked by LUT weight. Among feature books, sync and wilds
are 50/50. Among wild books the count mix is 80/15/4/1.
"""

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any

from ways_paint import BONUS_PAYING

FEATURE_RATE = 0.04
SYNC_PAIRS = ((0, 5), (1, 4), (2, 3))
WILD_COUNT_BANDS = (
    (80, 1),
    (15, 2),
    (4, 3),
    (1, 4),
)
FEATURE_TYPES = ("syncReels", "placeWilds")


def feature_bucket(book_id: int) -> int | None:
    """Every 25th book is a feature book (exactly 4% when ids are 0..N-1)."""
    ident = int(book_id)
    if ident < 0 or ident % 25 != 0:
        return None
    return ident // 25


def should_feature(book_id: int) -> bool:
    return feature_bucket(book_id) is not None


def feature_spec(book_id: int) -> dict[str, Any]:
    bucket = feature_bucket(book_id)
    if bucket is None:
        raise ValueError(f"book {book_id} is not a feature book")
    if bucket % 2 == 0:
        pair = SYNC_PAIRS[bucket % len(SYNC_PAIRS)]
        return {"kind": "syncReels", "reels": [int(pair[0]), int(pair[1])]}
    roll = bucket // 2 % 100
    count = 1
    acc = 0
    for share, n_wild in WILD_COUNT_BANDS:
        acc += share
        if roll < acc:
            count = n_wild
            break
    rng = random.Random(1_000_003 * int(book_id) + 17)
    cells = [(reel, row) for reel in range(6) for row in range(4)]
    rng.shuffle(cells)
    return {"kind": "placeWilds", "positions": [{"reel": reel, "row": row} for reel, row in cells[:count]]}


def _cell_name(cell) -> str:
    if isinstance(cell, dict):
        return str(cell.get("name") or "")
    return getattr(cell, "name", str(cell))


def _set_cell(col: list, row: int, name: str) -> None:
    payload = {"name": name}
    if name == "W":
        payload["wild"] = True
    if name == "S":
        payload["scatter"] = True
    if row < 0 or row >= len(col):
        return
    if isinstance(col[row], dict):
        col[row] = payload
    else:
        col[row] = name


def visible_grid(board: list) -> list[list[str]]:
    grid = []
    for col in board:
        names = [_cell_name(cell) for cell in col]
        if len(names) >= 6:
            names = names[1:5]
        grid.append(names[:4])
    return grid


def apply_spec_to_reveal_board(board: list, spec: dict[str, Any]) -> list:
    """Mutate a padded 6×6 or visible 6×4 reveal board to match the feature."""
    if spec["kind"] == "syncReels":
        left, right = spec["reels"]
        board[right] = [cell if not isinstance(cell, dict) else dict(cell) for cell in board[left]]
        return board
    for pos in spec.get("positions") or []:
        reel = int(pos["reel"])
        row = int(pos["row"])
        col = board[reel]
        padded = len(col) >= 6
        target = row + 1 if padded else row
        if 0 <= reel < len(board) and 0 <= target < len(col):
            if _cell_name(col[target]) == "S":
                continue
            _set_cell(col, target, "W")
    return board


def ways_detail(board: list[list[str]]) -> tuple[float, list[dict]]:
    """Left-to-right ways with W substituting, including reel-0 wilds."""
    paying = list(BONUS_PAYING)
    starters: list[str] = []
    seen: set[str] = set()
    for name in board[0]:
        if name in paying and name not in seen:
            seen.add(name)
            starters.append(name)
    if "W" in board[0]:
        for symbol in paying:
            if symbol not in seen:
                seen.add(symbol)
                starters.append(symbol)
    wins = []
    total = 0.0
    n_reels = len(board)
    for symbol in starters:
        kind = 0
        ways = 1
        positions = []
        for reel in range(n_reels):
            cells = []
            for row, name in enumerate(board[reel]):
                if name == symbol or name == "W":
                    cells.append({"reel": reel, "row": row + 1})
            if not cells:
                break
            kind += 1
            ways *= len(cells)
            positions.extend(cells)
        from game_config import WAYS_PAYTABLE

        pay = WAYS_PAYTABLE.get((kind, symbol))
        if pay:
            win = round(pay * ways, 2)
            total += win
            wins.append(
                {
                    "symbol": symbol,
                    "kind": kind,
                    "win": win,
                    "positions": positions,
                    "meta": {
                        "ways": ways,
                        "globalMult": 1,
                        "winWithoutMult": win,
                        "symbolMult": 0,
                    },
                }
            )
    return round(total, 2), wins


def scatter_count(board: list[list[str]]) -> int:
    return sum(1 for col in board for name in col if name == "S")


def feature_event(spec: dict[str, Any], index: int) -> dict[str, Any]:
    event = {"index": index, "type": "baseFeature", "kind": spec["kind"]}
    if spec["kind"] == "syncReels":
        event["reels"] = list(spec["reels"])
    else:
        event["positions"] = [
            {"reel": int(pos["reel"]), "row": int(pos["row"]) + 1} for pos in spec["positions"]
        ]
    return event


def _cents(pay: float) -> int:
    return int(round(pay * 100))


def _rebuild_base_tail(pay: float, wins: list[dict], start_index: int) -> list[dict]:
    cents = _cents(pay)
    events = []
    if wins and cents > 0:
        events.append(
            {
                "index": start_index,
                "type": "winInfo",
                "totalWin": cents,
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
            }
        )
        events.append({"index": start_index + 1, "type": "setWin", "amount": cents, "winLevel": 1})
    events.append({"index": start_index + len(events), "type": "setTotalWin", "amount": cents})
    events.append({"index": start_index + len(events), "type": "finalWin", "amount": cents})
    for offset, event in enumerate(events):
        event["index"] = start_index + offset
    return events


def apply_feature_to_book(book: dict) -> bool:
    """Stamp a feature onto a non-bonus base/ante book. Returns True if changed."""
    if not should_feature(int(book.get("id") or 0)):
        return False
    events = list(book.get("events") or [])
    if any(event.get("type") == "freeSpinTrigger" for event in events):
        return False
    if any(event.get("type") == "baseFeature" for event in events):
        return False
    reveal_at = next((i for i, event in enumerate(events) if event.get("type") == "reveal"), None)
    if reveal_at is None:
        return False
    spec = feature_spec(int(book["id"]))
    board = deepcopy(events[reveal_at]["board"])
    apply_spec_to_reveal_board(board, spec)
    names = visible_grid(board)
    if scatter_count(names) >= 3:
        return False
    events[reveal_at]["board"] = board
    pay, wins = ways_detail(names)
    feature = feature_event(spec, 0)
    tail = _rebuild_base_tail(pay, wins, 2)
    book["events"] = [feature, events[reveal_at], *tail]
    for index, event in enumerate(book["events"]):
        event["index"] = index
    book["payoutMultiplier"] = _cents(pay)
    book["baseGameWins"] = pay
    book["freeGameWins"] = 0.0
    return True


def classify_feature(book: dict) -> str | None:
    events = book.get("events") or []
    feat = next((event for event in events if event.get("type") == "baseFeature"), None)
    if not feat:
        return None
    if feat.get("kind") == "syncReels":
        return "feature_sync"
    count = max(1, min(4, len(feat.get("positions") or [])))
    return f"feature_w{count}"


def assert_feature_mix(book_ids: list[int]) -> dict[str, int]:
    """Sanity counts for tests / pack logs."""
    counts = {"feature": 0, "sync": 0, "wilds": 0, "w1": 0, "w2": 0, "w3": 0, "w4": 0}
    for book_id in book_ids:
        if not should_feature(book_id):
            continue
        counts["feature"] += 1
        spec = feature_spec(book_id)
        if spec["kind"] == "syncReels":
            counts["sync"] += 1
        else:
            counts["wilds"] += 1
            counts[f"w{len(spec['positions'])}"] += 1
    return counts
