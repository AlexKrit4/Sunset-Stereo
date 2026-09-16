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
