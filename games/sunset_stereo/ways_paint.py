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


def _best_single(tenths: int, cap: tuple[int, ...]) -> tuple[str, tuple[int, ...]] | None:
    idx = bisect.bisect_right(CATALOG_KEYS, tenths) - 1
    scanned = 0
    while idx >= 0 and scanned < 80:
        pay = CATALOG_KEYS[idx]
        for combo in CATALOG[pay]:
            if _fits(combo[1], cap):
                return combo
        idx -= 1
        scanned += 1
    return None


@lru_cache(maxsize=200_000)
def plan_tenths(tenths: int, cap: tuple[int, ...]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    """Return one or two ways combos that pay tenths, or the closest under it."""
    tenths = max(2, min(int(tenths), TENTHS_CAP))
    exact = [combo for combo in CATALOG.get(tenths, ()) if _fits(combo[1], cap)]
    if exact:
        return (exact[len(exact) // 2],)

    first = _best_single(tenths, cap)
    if first is None:
        return (("L5", (1, 1, 1)),)
    rest = tenths - _combo_pay(first)
    if rest >= 2:
        left = _subtract(cap, first[1])
        second = _best_single(rest, left)
        if second is not None and second[0] != first[0]:
            return (first, second)
    return (first,)


def plan_payout(target: float, cap: tuple[int, ...] | None = None) -> tuple[tuple[str, tuple[int, ...]], ...]:
    use_cap = cap or (ROWS,) * REELS
    return plan_tenths(to_tenths(target), tuple(int(v) for v in use_cap))


def planned_tenths(plan: tuple[tuple[str, tuple[int, ...]], ...]) -> int:
    return sum(_combo_pay(combo) for combo in plan)


def _permute(sim: int, mod: int) -> int:
    return (int(sim) * 1103515245 + 12345) % max(mod, 1)


def payout_target(mode: str, criteria: str, sim: int) -> float | None:
    """Deterministic 1× target for a book. None means 'no constructed payout'."""
    if criteria in {"0"}:
        return 0.0
    if criteria == "wincap":
        return 15000.0
    lane = _permute(sim, 10_000)

    if criteria == "basegame":
        if lane < 3800:
            return from_tenths(2 + (lane % 8))  # 0.2–0.9
        if lane < 5600:
            return from_tenths(10 + _permute(sim, 40))  # 1.0–4.9
        if lane < 7200:
            return from_tenths(50 + _permute(sim, 150))  # 5.0–19.9
        if lane < 8600:
            return from_tenths(200 + _permute(sim, 800))  # 20–99.9
        if lane < 9500:
            return from_tenths(1000 + _permute(sim, 4000))  # 100–499.9
        return from_tenths(5000 + _permute(sim, 20_000))  # 500–2499.9

    if criteria in {"freegame", "freegame4"}:
        if mode == "scatter" and criteria == "freegame":
            if lane < 6200:
                return from_tenths(100 + _permute(sim, 900))  # 10–99.9
            if lane < 8800:
                return from_tenths(1000 + _permute(sim, 4000))
            if lane < 9700:
                return from_tenths(5000 + _permute(sim, 15000))
            return from_tenths(20000 + _permute(sim, 80_000))
        if criteria == "freegame4":
            if lane < 3500:
                return from_tenths(120 + _permute(sim, 880))
            if lane < 7000:
                return from_tenths(1000 + _permute(sim, 4000))
            if lane < 9000:
                return from_tenths(5000 + _permute(sim, 20000))
            return from_tenths(25000 + _permute(sim, 90_000))
        if lane < 4500:
            return from_tenths(100 + _permute(sim, 500))  # 10–59.9
        if lane < 7500:
            return from_tenths(600 + _permute(sim, 1400))
        if lane < 9200:
            return from_tenths(2000 + _permute(sim, 8000))
        return from_tenths(10000 + _permute(sim, 50_000))

    if criteria == "dead":
        if mode == "wildbonus":
            if lane < 3500:
                return from_tenths(50 + _permute(sim, 100))  # 5–14.9
            if lane < 7000:
                return from_tenths(150 + _permute(sim, 250))
            if lane < 9000:
                return from_tenths(400 + _permute(sim, 500))
            return from_tenths(900 + _permute(sim, 1349))  # up to 224.9
        if lane < 2800:
            return from_tenths(30 + _permute(sim, 50))  # 3–7.9
        if lane < 5600:
            return from_tenths(80 + _permute(sim, 120))
        if lane < 8000:
            return from_tenths(200 + _permute(sim, 200))
        return from_tenths(400 + _permute(sim, 549))  # up to 94.9

    if criteria == "recoup":
        if mode == "wildbonus":
            if lane < 4000:
                return from_tenths(2250 + _permute(sim, 1750))  # 225–399.9
            if lane < 7200:
                return from_tenths(4000 + _permute(sim, 4000))
            if lane < 9000:
                return from_tenths(8000 + _permute(sim, 12000))
            return from_tenths(20000 + _permute(sim, 80_000))
        if lane < 4200:
            return from_tenths(950 + _permute(sim, 450))  # 95–139.9
        if lane < 7400:
            return from_tenths(1400 + _permute(sim, 1100))
        if lane < 9100:
            return from_tenths(2500 + _permute(sim, 7500))
        return from_tenths(10000 + _permute(sim, 49_999))

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
