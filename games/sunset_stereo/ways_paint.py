"""Construct 6×4 ways boards that pay a chosen multiple.

Every paying book gets a deterministic target from its sim id so the LUT
is not a pile of 0.2× / 0.4× clones. Scatter/wild locks occupy cells and
are left in place.
"""

from __future__ import annotations

import bisect
import itertools
import random
from functools import lru_cache

from game_config import BONUS_PAYING, WAYS_PAYTABLE

ROWS = 4
REELS = 6
TENTHS_CAP = 150_000  # 15000× in tenths of 1×


def to_tenths(value: float) -> int:
    return int(round(float(value) * 10.0))


def from_tenths(tenths: int) -> float:
    return round(tenths / 10.0, 2)


def _build_catalog() -> dict[int, list[tuple[str, tuple[int, ...]]]]:
    catalog: dict[int, list[tuple[str, tuple[int, ...]]]] = {}
    for symbol in BONUS_PAYING:
        for kind in (3, 4, 5, 6):
            unit = to_tenths(WAYS_PAYTABLE[(kind, symbol)])
            for counts in itertools.product(range(1, ROWS + 1), repeat=kind):
                ways = 1
                for count in counts:
                    ways *= count
                tenths = unit * ways
                if tenths <= 0 or tenths > TENTHS_CAP:
                    continue
                catalog.setdefault(tenths, []).append((symbol, counts))
    return catalog


CATALOG = _build_catalog()
CATALOG_KEYS = tuple(sorted(CATALOG))


def _fits(counts: tuple[int, ...], cap: tuple[int, ...]) -> bool:
    return all(counts[reel] <= cap[reel] for reel in range(len(counts)))


def _subtract(cap: tuple[int, ...], counts: tuple[int, ...]) -> tuple[int, ...]:
    left = list(cap)
    for reel, count in enumerate(counts):
        left[reel] -= count
    return tuple(left)


def _combo_pay(combo: tuple[str, tuple[int, ...]]) -> int:
    symbol, counts = combo
    ways = 1
    for count in counts:
        ways *= count
    return to_tenths(WAYS_PAYTABLE[(len(counts), symbol)]) * ways


def _entries() -> list[tuple[int, str, tuple[int, ...]]]:
    items = []
    for pay, combos in CATALOG.items():
        seen: set[str] = set()
        for symbol, counts in combos:
            if symbol in seen:
                continue
            seen.add(symbol)
            items.append((pay, symbol, counts))
    return items


def _build_feasible(cap: tuple[int, ...]) -> dict[int, tuple[tuple[str, tuple[int, ...]], ...]]:
    entries = _entries()
    kind3 = [item for item in entries if len(item[2]) == 3]
    feasible: dict[int, tuple[tuple[str, tuple[int, ...]], ...]] = {}
    for pay, symbol, counts in entries:
        if _fits(counts, cap):
            feasible.setdefault(pay, ((symbol, counts),))
    twos: dict[int, tuple[tuple[str, tuple[int, ...]], ...]] = {}
    for pay1, symbol1, counts1 in entries:
        if not _fits(counts1, cap):
            continue
        left = _subtract(cap, counts1)
        for pay2, symbol2, counts2 in entries:
            if symbol2 == symbol1 or not _fits(counts2, left):
                continue
            plan = ((symbol1, counts1), (symbol2, counts2))
            twos.setdefault(pay1 + pay2, plan)
            feasible.setdefault(pay1 + pay2, plan)
    for pay12, plan in twos.items():
        caps = list(cap)
        used = {symbol for symbol, _ in plan}
        for _symbol, counts in plan:
            for reel, count in enumerate(counts):
                caps[reel] -= count
        left = tuple(caps)
        for pay3, symbol3, counts3 in kind3:
            if symbol3 in used or not _fits(counts3, left):
                continue
            feasible.setdefault(pay12 + pay3, plan + ((symbol3, counts3),))
    return feasible


FEASIBLE = _build_feasible((ROWS,) * REELS)
FEASIBLE_R2 = _build_feasible((ROWS, ROWS, ROWS - 1, ROWS, ROWS, ROWS))
FEASIBLE_KEYS = tuple(sorted(FEASIBLE))
FEASIBLE_R2_KEYS = tuple(sorted(FEASIBLE_R2))


def _lookup_feasible(tenths: int, cap: tuple[int, ...]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    table = FEASIBLE_R2 if cap[2] < ROWS else FEASIBLE
    keys = FEASIBLE_R2_KEYS if cap[2] < ROWS else FEASIBLE_KEYS
    tenths = max(2, min(int(tenths), TENTHS_CAP))
    if tenths in table:
        return table[tenths]
    idx = bisect.bisect_right(keys, tenths) - 1
    if idx < 0:
        return (("L5", (1, 1, 1)),)
    return table[keys[idx]]


@lru_cache(maxsize=200_000)
def plan_tenths(tenths: int, cap: tuple[int, ...]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    return _lookup_feasible(tenths, cap)


def plan_payout(target: float, cap: tuple[int, ...] | None = None) -> tuple[tuple[str, tuple[int, ...]], ...]:
    use_cap = cap or (ROWS,) * REELS
    return plan_tenths(to_tenths(target), tuple(int(v) for v in use_cap))


def planned_tenths(plan: tuple[tuple[str, tuple[int, ...]], ...]) -> int:
    return sum(_combo_pay(combo) for combo in plan)


def _permute(sim: int, mod: int) -> int:
    return (int(sim) * 1103515245 + 12345) % max(mod, 1)


def _keys_between(lo: int, hi: int) -> tuple[int, ...]:
    return tuple(key for key in FEASIBLE_KEYS if lo <= key < hi)


BANDS = {
    "tiny": _keys_between(2, 10),
    "small": _keys_between(10, 50),
    "mid": _keys_between(50, 200),
    "chunk": _keys_between(200, 1000),
    "big": _keys_between(1000, 5000),
    "huge": _keys_between(5000, 25000),
    "bonus_low": _keys_between(100, 1000),
    "bonus_mid": _keys_between(1000, 5000),
    "bonus_high": _keys_between(5000, 40000),
    "dead": _keys_between(30, 950),
    "dead_wild": _keys_between(50, 2250),
    "recoup": _keys_between(950, 150000),
    "recoup_wild": _keys_between(2250, 150000),
}


def pick_feasible(band: str, sim: int) -> float:
    keys = BANDS[band]
    return from_tenths(keys[(int(sim) * 7919) % len(keys)])


def payout_target(mode: str, criteria: str, sim: int) -> float | None:
    """Deterministic 1× target for a book. None means a random natural ways hit."""
    if criteria in {"0"}:
        return 0.0
    if criteria == "wincap":
        return 15000.0
    lane = _permute(sim, 10_000)

    if criteria == "basegame":
        if lane < 3800:
            return pick_feasible("tiny", sim)
        if lane < 5600:
            return pick_feasible("small", sim)
        if lane < 7000:
            return pick_feasible("mid", sim)
        if lane < 8400:
            return pick_feasible("chunk", sim)
        if lane < 9400:
            return pick_feasible("big", sim)
        if lane < 9700:
            return pick_feasible("huge", sim)
        return None

    if criteria in {"freegame", "freegame4"}:
        if mode == "scatter" and criteria == "freegame":
            if lane < 7000:
                return pick_feasible("bonus_low", sim)
            return pick_feasible("bonus_mid", sim)
        if criteria == "freegame4" or lane >= 8800:
            if lane < 7000:
                return pick_feasible("bonus_mid", sim)
            return pick_feasible("bonus_high", sim)
        if lane < 5000:
            return pick_feasible("bonus_low", sim)
        if lane < 8500:
            return pick_feasible("bonus_mid", sim)
        return pick_feasible("bonus_high", sim)

    if criteria == "dead":
        return pick_feasible("dead_wild" if mode == "wildbonus" else "dead", sim)

    if criteria == "recoup":
        return pick_feasible("recoup_wild" if mode == "wildbonus" else "recoup", sim)

    return None


def filler_symbol(paying: set[str], reel: int, rng: random.Random) -> str:
    choices = [symbol for symbol in BONUS_PAYING if symbol not in paying]
    return choices[(reel + rng.randrange(len(choices))) % len(choices)]


def row_picks(count: int, blocked: set[int], rng: random.Random) -> list[int]:
    free = [row for row in range(ROWS) if row not in blocked]
    rng.shuffle(free)
    if len(free) < count:
        return free
    return sorted(free[:count])


# Low-pay bias, independent per cell. Same mix the generator uses for dead fills.
ZERO_WEIGHTS = (4, 5, 6, 7, 8, 14, 15, 16, 17, 18)
PAYING_SET = set(BONUS_PAYING)


def _pick_zero(rng) -> str:
    return rng.choices(BONUS_PAYING, weights=ZERO_WEIGHTS, k=1)[0]


def _paying_names(col: list[str]) -> set[str]:
    return {name for name in col if name in PAYING_SET}


def visible_ways_win(board: list[list[str]]) -> float:
    """Ways total for a 6×4 name grid. Matches Ways.get_ways_data without Symbol objects."""
    starters: list[str] = []
    seen: set[str] = set()
    for name in board[0]:
        if name in PAYING_SET and name not in seen:
            seen.add(name)
            starters.append(name)
    if "W" in board[0]:
        for symbol in BONUS_PAYING:
            if symbol not in seen:
                seen.add(symbol)
                starters.append(symbol)
    total = 0.0
    n_reels = len(board)
    for symbol in starters:
        kind = 0
        ways = 1
        for reel in range(n_reels):
            count = sum(1 for name in board[reel] if name == symbol)
            wilds = sum(1 for name in board[reel] if name == "W")
            if count + wilds == 0:
                break
            kind += 1
            ways *= count + wilds
        pay = WAYS_PAYTABLE.get((kind, symbol))
        if pay:
            total += pay * ways
    return round(total, 2)


def is_stacked_column_board(board: list[list[str]]) -> bool:
    """True when every reel is a 3+ stack of one paying symbol (the old dead-fill look)."""
    if not board:
        return False
    for col in board:
        paying = [name for name in col if name in PAYING_SET]
        if len(paying) < 3 or len(set(paying)) != 1:
            return False
    return True


def _unlocked_rows(reel: int, locked: dict[tuple[int, int], str]) -> list[int]:
    return [row for row in range(ROWS) if (reel, row) not in locked]


def _cap_reel_stacks(board: list[list[str]], reel: int, locked: dict[tuple[int, int], str], rng, forbidden: set[str] | None = None) -> None:
    """Keep at most two of the same paying symbol on a reel so it does not look like a column."""
    pool = [symbol for symbol in BONUS_PAYING if symbol not in (forbidden or set())]
    if not pool:
        return
    unlocked = _unlocked_rows(reel, locked)
    for _ in range(12):
        counts: dict[str, int] = {}
        for name in board[reel]:
            if name in PAYING_SET:
                counts[name] = counts.get(name, 0) + 1
        heavy = [symbol for symbol, count in counts.items() if count >= 3]
        if not heavy:
            return
        moved = False
        for row in unlocked:
            name = board[reel][row]
            if name not in heavy:
                continue
            alt = [symbol for symbol in pool if symbol != name]
            if not alt:
                return
            board[reel][row] = rng.choice(alt)
            moved = True
            break
        if not moved:
            return


def _blocked_starters(board: list[list[str]]) -> set[str]:
    """Paying symbols on reel 0 that already continue onto reel 1 (or through a wild)."""
    starters = set(PAYING_SET) if "W" in board[0] else _paying_names(board[0])
    nxt = set(PAYING_SET) if "W" in board[1] else _paying_names(board[1])
    return starters & nxt


def _break_three_oak(board: list[list[str]], locked: dict[tuple[int, int], str], rng) -> None:
    """Kill 3-oak ways by replacing reel-2 (or reel-1) cells that would complete a pay."""
    blocked = _blocked_starters(board)
    if "W" in board[2] and blocked:
        forbidden = set(PAYING_SET) if "W" in board[0] else _paying_names(board[0])
        pool = [symbol for symbol in BONUS_PAYING if symbol not in forbidden]
        if pool:
            for row in _unlocked_rows(1, locked):
                if board[1][row] in forbidden or board[1][row] == "W":
                    board[1][row] = rng.choice(pool)
            _cap_reel_stacks(board, 1, locked, rng, forbidden=forbidden)
        blocked = _blocked_starters(board)

    if not blocked:
        return
    pool = [symbol for symbol in BONUS_PAYING if symbol not in blocked]
    if not pool:
        forbidden = set(PAYING_SET) if "W" in board[0] else _paying_names(board[0])
        pool = [symbol for symbol in BONUS_PAYING if symbol not in forbidden]
        if not pool:
            return
        for row in _unlocked_rows(1, locked):
            if board[1][row] in forbidden or board[1][row] == "W":
                board[1][row] = rng.choice(pool)
        _cap_reel_stacks(board, 1, locked, rng, forbidden=forbidden)
        blocked = _blocked_starters(board)
        pool = [symbol for symbol in BONUS_PAYING if symbol not in blocked]
        if not pool:
            return

    for row in _unlocked_rows(2, locked):
        if board[2][row] in blocked or board[2][row] == "W":
            board[2][row] = rng.choice(pool)
    _cap_reel_stacks(board, 2, locked, rng, forbidden=blocked)


def paint_mixed_dead(rng, locked: dict[tuple[int, int], str] | None = None) -> list[list[str]]:
    """Independent per-cell fill: mixed symbols, no 3-oak, no stacked columns."""
    locked = dict(locked or {})
    board: list[list[str]] = [[""] * ROWS for _ in range(REELS)]
    for _ in range(40):
        for reel in range(REELS):
            for row in range(ROWS):
                if (reel, row) in locked:
                    board[reel][row] = locked[(reel, row)]
                else:
                    board[reel][row] = _pick_zero(rng)
        for reel in range(REELS):
            _cap_reel_stacks(board, reel, locked, rng)
        _break_three_oak(board, locked, rng)
        if visible_ways_win(board) == 0 and not is_stacked_column_board(board):
            return board
    _break_three_oak(board, locked, rng)
    return board


def paint_mixed_pads(rng, visible: list[list[str]] | None = None, forbidden: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Padding cells, also mixed — not a copy of the visible stack."""
    banned = set(forbidden or ())
    pool = [symbol for symbol in BONUS_PAYING if symbol not in banned] or list(BONUS_PAYING)
    tops = [_pick_pool(rng, pool) for _ in range(REELS)]
    bottoms = [_pick_pool(rng, pool) for _ in range(REELS)]
    if not visible:
        return tops, bottoms
    for reel in range(REELS):
        stack = {name for name in visible[reel] if name in PAYING_SET}
        if len(stack) == 1:
            only = next(iter(stack))
            alt = [symbol for symbol in pool if symbol != only] or pool
            if tops[reel] == only:
                tops[reel] = rng.choice(alt)
            if bottoms[reel] == only:
                bottoms[reel] = rng.choice(alt)
    return tops, bottoms


def _pick_pool(rng, pool: list[str]) -> str:
    if not pool:
        return _pick_zero(rng)
    if len(pool) == 1:
        return pool[0]
    weights = [ZERO_WEIGHTS[BONUS_PAYING.index(symbol)] for symbol in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


def _oak_kind(board: list[list[str]], symbol: str) -> int:
    kind = 0
    for col in board:
        if any(name == symbol or name == "W" for name in col):
            kind += 1
        else:
            break
    return kind


def _break_unwanted_oaks(board: list[list[str]], occupied: dict[tuple[int, int], str], keep: set[str], rng) -> None:
    """Kill extra 3-oaks of filler symbols without moving win/scatter/wild cells."""
    pool = [symbol for symbol in BONUS_PAYING if symbol not in keep]
    if not pool:
        return
    for _ in range(24):
        extras = [symbol for symbol in BONUS_PAYING if symbol not in keep and _oak_kind(board, symbol) >= 3]
        if not extras:
            return
        symbol = extras[0]
        moved = False
        for reel in (2, 1, 0, 3, 4, 5):
            for row in _unlocked_rows(reel, occupied):
                if board[reel][row] != symbol:
                    continue
                board[reel][row] = _pick_pool(rng, pool)
                moved = True
            if _oak_kind(board, symbol) < 3:
                break
        if not moved:
            return


def paint_hit_fillers(occupied: dict[tuple[int, int], str], rng) -> list[list[str]]:
    """Keep win/scatter/wild cells; mix every other cell with non-winning symbols."""
    occupied = dict(occupied or {})
    keep = {name for name in occupied.values() if name in PAYING_SET}
    pool = [symbol for symbol in BONUS_PAYING if symbol not in keep]
    if not pool:
        pool = list(BONUS_PAYING)
    board: list[list[str]] = [[""] * ROWS for _ in range(REELS)]
    for _ in range(40):
        for reel in range(REELS):
            for row in range(ROWS):
                if (reel, row) in occupied:
                    board[reel][row] = occupied[(reel, row)]
                else:
                    board[reel][row] = _pick_pool(rng, pool)
        for reel in range(REELS):
            unlocked = _unlocked_rows(reel, occupied)
            for _ in range(8):
                fillers = [board[reel][row] for row in unlocked]
                if len(fillers) < 3 or len(set(fillers)) >= 2:
                    break
                row = unlocked[rng.randrange(len(unlocked))]
                alt = [symbol for symbol in pool if symbol != board[reel][row]]
                if not alt:
                    break
                board[reel][row] = _pick_pool(rng, alt)
            _cap_reel_stacks(board, reel, occupied, rng, forbidden=keep)
        _break_unwanted_oaks(board, occupied, keep, rng)
        leaked = any(
            (reel, row) not in occupied and board[reel][row] in keep
            for reel in range(REELS)
            for row in range(ROWS)
        )
        extras = [symbol for symbol in BONUS_PAYING if symbol not in keep and _oak_kind(board, symbol) >= 3]
        stacked = filler_column_reels(board, occupied)
        if not leaked and not extras and not stacked:
            return board
    return board


def delay_opening_win(seed: int) -> bool:
    """About 90% of bonus books open on a dead extra play."""
    return int(seed) % 10 != 0


def opening_respin_count(seed: int) -> int:
    """2 or 3 hold-respins for the first paying extra play."""
    return 3 if int(seed) % 2 else 2


def growing_hold_stages(
    occupied: dict[tuple[int, int], str],
    n_respins: int = 2,
) -> list[dict[tuple[int, int], str]]:
    """Build 2–3 respins that grow into the final occupied win.

    Returns n_respins+1 occupied maps. The last map is the full win. Sticky
    wilds stay in every stage. Earlier stages are a valid 3-oak subset when
    the final win has enough cells; otherwise the same lock is shown while
    fillers change.
    """
    occupied = dict(occupied or {})
    n_respins = 2 if n_respins < 3 else 3
    sticky = {key: name for key, name in occupied.items() if name == "W"}
    by_reel: list[list[tuple[int, int]]] = [[] for _ in range(REELS)]
    for key in occupied:
        by_reel[key[0]].append(key)
    kind = 0
    for reel in range(REELS):
        if by_reel[reel]:
            kind += 1
        else:
            break

    def add_reel(dst: dict[tuple[int, int], str], reel: int, one: bool) -> None:
        cells = by_reel[reel]
        if not cells:
            return
        if one:
            non_wild = [cell for cell in cells if occupied[cell] != "W"]
            cell = (non_wild or cells)[0]
            dst[cell] = occupied[cell]
            return
        for cell in cells:
            dst[cell] = occupied[cell]

    core: dict[tuple[int, int], str] = dict(sticky)
    for reel in range(min(3, kind)):
        add_reel(core, reel, one=True)
    if len(core) < 3 and occupied:
        core = dict(occupied)

    rest = sorted(key for key in occupied if key not in core)
    stages = [core]
    if rest:
        parts = n_respins - 1
        chunk = max(1, (len(rest) + parts - 1) // max(1, parts))
        grown = dict(core)
        for index, key in enumerate(rest):
            grown[key] = occupied[key]
            last_in_part = (index + 1) % chunk == 0 or index == len(rest) - 1
            if last_in_part and grown != stages[-1]:
                stages.append(dict(grown))
            if len(stages) >= n_respins:
                break
    full = dict(occupied)
    if stages[-1] != full:
        stages.append(full)
    while len(stages) < n_respins + 1:
        stages.insert(-1, dict(stages[-1]))
    return stages[-n_respins - 1 :]


def filler_column_reels(board: list[list[str]], occupied: dict[tuple[int, int], str]) -> list[int]:
    """Reels whose non-win cells are a 3+ stack of one filler symbol."""
    stacked = []
    for reel, col in enumerate(board):
        fillers = [col[row] for row in range(len(col)) if (reel, row) not in occupied and col[row] in PAYING_SET]
        if len(fillers) >= 3 and len(set(fillers)) == 1:
            stacked.append(reel)
    return stacked
