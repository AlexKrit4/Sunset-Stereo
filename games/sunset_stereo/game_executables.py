import random
from copy import deepcopy

from game_calculations import GameCalculations, MAX_HOLD_RESPINS
from game_config import BONUS_PAYING, BUY_BONUS_COST, BUY_WILD_COST, REEL2, SCATTER_REELS
from game_events import hold_respin_event, place_wild_event
from src.calculations.ways import Ways
from src.events.events import reveal_event, wincap_event
from ways_paint import (
    paint_hit_fillers,
    paint_mixed_dead,
    paint_mixed_pads,
    plan_payout,
    payout_target,
    row_picks,
    visible_ways_win,
)


def quantize_win(value: float) -> float:
    """RGS payouts are integer cents of 0.10x (multiples of 10)."""
    return round(round(value * 10.0) / 10.0, 2)


MIXES = {
    "zero": [4, 5, 6, 7, 8, 14, 15, 16, 17, 18],
    "low": [6, 7, 8, 9, 10, 12, 13, 13, 14, 14],
    "mid": [10, 11, 12, 12, 12, 10, 10, 10, 10, 11],
    "high": [22, 18, 14, 12, 10, 6, 6, 5, 4, 3],
    "wincap": [48, 22, 10, 6, 4, 3, 3, 2, 1, 1],
}


class GameExecutables(GameCalculations):
    def remaining_to_wincap(self) -> float:
        room = self.config.wincap - self.win_manager.running_bet_win
        return quantize_win(max(0.0, room))

    def clamp_win_data_to_ceiling(self) -> bool:
        room = self.remaining_to_wincap()
        total = float(self.win_data.get("totalWin", 0) or 0)
        crossed = self.win_manager.running_bet_win + total >= self.config.wincap and (
            total > 0 or self.win_manager.running_bet_win >= self.config.wincap
        )
        if total > room:
            self.win_data["totalWin"] = room
        return crossed

    def pay_current_board(self) -> None:
        hit_cap = self.clamp_win_data_to_ceiling()
        Ways.record_ways_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        Ways.emit_wayswin_events(self)
        if self.win_manager.running_bet_win > self.config.wincap:
            overflow = self.win_manager.running_bet_win - self.config.wincap
            self.win_manager.running_bet_win = float(self.config.wincap)
            self.win_manager.spin_win = max(0.0, self.win_manager.spin_win - overflow)
        if (
            (hit_cap or self.win_manager.running_bet_win >= self.config.wincap)
            and not self.wincap_triggered
        ):
            self.wincap_triggered = True
            wincap_event(self)

    def evaluate_ways_board(self, emit_events: bool = True):
        self.win_data = Ways.get_ways_data(self.config, self.board)
        self.win_data["totalWin"] = quantize_win(self.win_data.get("totalWin", 0))
        for win in self.win_data.get("wins", []):
            win["win"] = quantize_win(win.get("win", 0))
            if "meta" in win and "winWithoutMult" in win["meta"]:
                win["meta"]["winWithoutMult"] = quantize_win(win["meta"]["winWithoutMult"])
        if not emit_events:
            return
        self.pay_current_board()

    def _conditions(self) -> dict:
        return self.get_current_distribution_conditions()

    def _pick(self, mix: str) -> str:
        weights = MIXES[mix]
        return random.choices(BONUS_PAYING, weights=weights, k=1)[0]

    def _fill_cells(self, mix: str, locked: set[tuple[int, int]] | None = None) -> None:
        locked = locked or set()
        self.refresh_special_syms()
        rows = self.config.num_rows
        board = [[None] * rows[reel] for reel in range(self.config.num_reels)]
        for reel in range(self.config.num_reels):
            for row in range(rows[reel]):
                if (reel, row) in locked:
                    board[reel][row] = self.board[reel][row]
                    continue
                board[reel][row] = self.create_symbol(self._pick(mix))
        self.board = board
        self.top_symbols = [self.create_symbol(self._pick(mix)) for _ in range(self.config.num_reels)]
        self.bottom_symbols = [self.create_symbol(self._pick(mix)) for _ in range(self.config.num_reels)]
        self.reel_positions = [random.randrange(256) for _ in range(self.config.num_reels)]
        self.get_special_symbols_on_board()
        self._apply_anticipation()

    def _apply_anticipation(self) -> None:
        self.anticipation = [0] * self.config.num_reels
        hits = []
        for reel in SCATTER_REELS:
            if any(cell.check_attribute("scatter") for cell in self.board[reel]):
                hits.append(reel)
        if len(hits) >= 2:
            start = hits[1] + 1 if len(hits) >= 3 else max(hits) + 1
            count = 1
            for reel in range(start, self.config.num_reels):
                self.anticipation[reel] = count
                count += 1

    def _place_scatters(self, count: int, require_reel2: bool) -> None:
        chosen: list[int] = []
        pool = list(SCATTER_REELS)
        if require_reel2:
            chosen.append(REEL2)
            pool = [reel for reel in pool if reel != REEL2]
        random.shuffle(pool)
        while len(chosen) < count and pool:
            chosen.append(pool.pop())
        for reel in SCATTER_REELS:
            for row, cell in enumerate(self.board[reel]):
                if cell.name == "S":
                    self.board[reel][row] = self.create_symbol(self._pick("low"))
        for reel in chosen:
            row = random.randrange(self.config.num_rows[reel])
            self.board[reel][row] = self.create_symbol("S")
        self.get_special_symbols_on_board()
        self._apply_anticipation()

    def _scatter_count(self) -> int:
        return self.count_special_symbols("scatter")

    def _locked_symbol_cells(self) -> dict[tuple[int, int], str]:
        locked: dict[tuple[int, int], str] = {}
        if not getattr(self, "board", None):
            return locked
        for reel, column in enumerate(self.board):
            for row, cell in enumerate(column):
                if cell is None:
                    continue
                if cell.name in {"S", "W"}:
                    locked[(reel, row)] = cell.name
        return locked

    def _available_counts(self, locked: dict[tuple[int, int], str]) -> tuple[int, ...]:
        caps = []
        for reel in range(self.config.num_reels):
            taken = sum(1 for row in range(self.config.num_rows[reel]) if (reel, row) in locked)
            caps.append(max(0, self.config.num_rows[reel] - taken))
        return tuple(caps)

    def paint_payout(self, target: float, locked: dict[tuple[int, int], str] | None = None) -> None:
        """Fill a unique-looking board whose ways total is as close as possible to target."""
        locked = dict(locked or {})
        cap = self._available_counts(locked)
        room = self.remaining_to_wincap()
        capped = min(max(target, 0.2), room) if room > 0 else max(target, 0.2)
        want = quantize_win(capped)
        plan = plan_payout(want, cap)
        paying = {symbol for symbol, _counts in plan}
        salt = sum(ord(ch) for ch in str(self.criteria)) + self.repeat_count * 13
        rng = random.Random((self.sim + 1) * 9176 + salt)
        occupied: dict[tuple[int, int], str] = dict(locked)
        rows = self.config.num_rows
        for symbol, counts in plan:
            for reel, count in enumerate(counts):
                blocked = {row for row in range(rows[reel]) if (reel, row) in occupied}
                for row in row_picks(count, blocked, rng):
                    occupied[(reel, row)] = symbol
        names = paint_hit_fillers(occupied, rng)
        board = [[None] * rows[reel] for reel in range(self.config.num_reels)]
        for reel in range(self.config.num_reels):
            for row in range(rows[reel]):
                board[reel][row] = self.create_symbol(names[reel][row])
        self.board = board
        tops, bottoms = paint_mixed_pads(rng, names, forbidden=paying)
        self.top_symbols = [self.create_symbol(name) for name in tops]
        self.bottom_symbols = [self.create_symbol(name) for name in bottoms]
        self.reel_positions = [rng.randrange(256) for _ in range(self.config.num_reels)]
        self.refresh_special_syms()
        self.get_special_symbols_on_board()
        self._apply_anticipation()

    def draw_board(self, emit_event: bool = True, trigger_symbol: str = "scatter") -> None:
        conditions = self._conditions()
        mix = "wincap" if conditions.get("force_wincap") else "mid"
        if self.gametype == self.config.freegame_type:
            self._fill_cells("low" if self.criteria == "dead" else mix)
            if emit_event:
                reveal_event(self)
            return

        require_reel2 = bool(conditions.get("force_reel2_scatter"))
        if conditions.get("force_freegame"):
            want = int(list(conditions["scatter_triggers"].keys())[0])
            for _ in range(40):
                self._fill_cells("mid")
                self._place_scatters(want, require_reel2)
                if self._scatter_count() == want:
                    break
        elif self.criteria == "basegame":
            target = payout_target(self.betmode, self.criteria, self.sim)
            if target is None:
                for _ in range(80):
                    self._fill_cells("mid")
                    if require_reel2:
                        self._place_scatters(1, True)
                    self.evaluate_ways_board(emit_events=False)
                    if 0 < float(self.win_data.get("totalWin", 0)) < 500 and self._scatter_count() < 3:
                        break
                else:
                    self.paint_payout(0.4, {(REEL2, 0): "S"} if require_reel2 else {})
            else:
                locked: dict[tuple[int, int], str] = {}
                if require_reel2:
                    locked[(REEL2, random.randrange(self.config.num_rows[REEL2]))] = "S"
                self.paint_payout(target, locked)
                if self._scatter_count() >= 3:
                    self._fill_cells("low")
                    if require_reel2:
                        self._place_scatters(1, True)
        elif self.criteria == "0":
            self._fill_no_win()
            if require_reel2:
                self._place_scatters(1, True)
        else:
            for _ in range(80):
                self._fill_cells("low")
                if require_reel2:
                    self._place_scatters(1, True)
                if self._scatter_count() < 3:
                    break
            else:
                self._fill_no_win()
                if require_reel2:
                    self._place_scatters(1, True)
        if emit_event:
            reveal_event(self)

    def _fill_no_win(self, locked: set[tuple[int, int]] | None = None) -> None:
        """Mixed per-cell board with no 3-oak ways. Not one symbol stacked down a reel."""
        locked = locked or set()
        locked_names: dict[tuple[int, int], str] = {}
        if getattr(self, "board", None):
            for reel, row in locked:
                locked_names[(reel, row)] = self.board[reel][row].name
        names = paint_mixed_dead(random, locked_names)
        rows = self.config.num_rows
        board = [[None] * rows[reel] for reel in range(self.config.num_reels)]
        for reel in range(self.config.num_reels):
            for row in range(rows[reel]):
                board[reel][row] = self.create_symbol(names[reel][row])
        self.board = board
        tops, bottoms = paint_mixed_pads(random, names)
        self.top_symbols = [self.create_symbol(name) for name in tops]
        self.bottom_symbols = [self.create_symbol(name) for name in bottoms]
        self.reel_positions = [random.randrange(256) for _ in range(self.config.num_reels)]
        self.refresh_special_syms()
        self.get_special_symbols_on_board()
        self._apply_anticipation()

    def respin_unlocked_cells(self, locked: set[tuple[int, int]], mix: str = "mid") -> None:
        force_wincap = bool(self._conditions().get("force_wincap"))
        if force_wincap:
            use = "wincap"
        elif mix == "zero":
            use = "low"
        else:
            use = mix
        self._fill_cells(use, locked=locked)

    def _dead_ceiling(self) -> float | None:
        if self.criteria != "dead":
            return None
        return BUY_WILD_COST if self.betmode == "wildbonus" else BUY_BONUS_COST

    def _restore_sticky(self, sticky: set[tuple[int, int]]) -> None:
        for reel, row in sticky:
            self.board[reel][row] = self.create_symbol("W")
        self.get_special_symbols_on_board()

    def _capture_board(self):
        return (
            deepcopy(self.board),
            list(self.top_symbols),
            list(self.bottom_symbols),
            list(self.reel_positions),
        )

    def _restore_board(self, snapshot) -> None:
        self.board, self.top_symbols, self.bottom_symbols, self.reel_positions = snapshot
        self.get_special_symbols_on_board()

    def _visible_names(self) -> list[list[str]]:
        return [[cell.name for cell in column] for column in self.board]

    def _apply_name_grid(self, names: list[list[str]], rng, forbidden: set[str] | None = None) -> None:
        rows = self.config.num_rows
        board = [[None] * rows[reel] for reel in range(self.config.num_reels)]
        for reel in range(self.config.num_reels):
            for row in range(rows[reel]):
                board[reel][row] = self.create_symbol(names[reel][row])
        self.board = board
        tops, bottoms = paint_mixed_pads(rng, names, forbidden=forbidden)
        self.top_symbols = [self.create_symbol(name) for name in tops]
        self.bottom_symbols = [self.create_symbol(name) for name in bottoms]
        self.reel_positions = [rng.randrange(256) for _ in range(self.config.num_reels)]
        self.refresh_special_syms()
        self.get_special_symbols_on_board()
        self._apply_anticipation()

    def _respin_without_growth(self, locked: set[tuple[int, int]], sticky: set[tuple[int, int]]) -> None:
        """Respin unlocked cells without adding ways. Locked winners stay put."""
        occupied: dict[tuple[int, int], str] = {}
        rows = self.config.num_rows
        for reel in range(self.config.num_reels):
            for row in range(rows[reel]):
                if (reel, row) in sticky:
                    occupied[(reel, row)] = "W"
                elif (reel, row) in locked:
                    occupied[(reel, row)] = self.board[reel][row].name
        want = visible_ways_win(self._visible_names())
        keep = {name for name in occupied.values() if name in BONUS_PAYING}
        names = None
        rng_used = None
        salt = (int(getattr(self, "sim", 0)) + 1) * 9176 + int(getattr(self, "fs", 0)) * 131
        salt += int(getattr(self, "repeat_count", 0)) * 13 + len(locked) * 19
        for attempt in range(16):
            rng = random.Random(salt ^ (attempt * 7919))
            candidate = paint_hit_fillers(occupied, rng)
            if visible_ways_win(candidate) != want:
                continue
            names = candidate
            rng_used = rng
            break
        if names is None:
            rng_used = random.Random(salt ^ 104729)
            names = self._visible_names()
        self._apply_name_grid(names, rng_used, forbidden=keep)

    def _hold_respin_loop(self, mix: str, sticky: set[tuple[int, int]]) -> None:
        locked: set[tuple[int, int]] = set(sticky)
        last_positive = {"totalWin": 0, "wins": []}
        ceiling = self._dead_ceiling()
        for step in range(MAX_HOLD_RESPINS + 1):
            snapshot = None
            if step > 0:
                snapshot = self._capture_board()
                self.respin_unlocked_cells(locked, mix=mix)
                self._restore_sticky(sticky)
            self.evaluate_ways_board(emit_events=False)
            total = float(self.win_data.get("totalWin", 0) or 0)
            projected = self.win_manager.running_bet_win + total
            over_limit = projected >= self.config.wincap or (ceiling is not None and projected >= ceiling)
            if step > 0 and total <= 0:
                reveal_event(self)
                self.win_data = last_positive
                break
            if step > 0 and over_limit:
                if snapshot is not None:
                    self._restore_board(snapshot)
                self._respin_without_growth(locked, sticky)
                reveal_event(self)
                self.win_data = last_positive
                break
            if step > 0:
                reveal_event(self)
            if total <= 0:
                break
            keys = self.winning_cell_keys() | sticky
            grown = any(key not in locked for key in keys)
            last_positive = deepcopy(self.win_data)
            if over_limit:
                locked = keys
                if step < MAX_HOLD_RESPINS:
                    hold_respin_event(self, locked, continuing=True)
                    self._respin_without_growth(locked, sticky)
                    reveal_event(self)
                    self.win_data = last_positive
                break
            if step > 0 and not grown:
                break
            locked = keys
            if step < MAX_HOLD_RESPINS:
                hold_respin_event(self, locked, continuing=True)
        self.pay_current_board()

    def _hold_respin_body(self, mix: str = "mid", sticky: set[tuple[int, int]] | None = None, painted: bool = False) -> None:
        sticky = set(sticky or ())
        if not painted:
            if mix == "zero":
                self._fill_no_win(sticky)
            else:
                self._fill_cells(mix)
            for reel, row in sticky:
                self.board[reel][row] = self.create_symbol("W")
            self.get_special_symbols_on_board()
            reveal_event(self)
        self._hold_respin_loop(mix, sticky)

    def _bonus_mix_for_room(self, lo: float, hi: float, remaining: int) -> str:
        if self._conditions().get("force_wincap"):
            return "wincap"
        room_hi = max(0.0, hi - self.win_manager.running_bet_win)
        room_lo = max(0.0, lo - self.win_manager.running_bet_win)
        if remaining <= 0:
            return "low"
        per = room_lo / remaining if remaining else 0
        if room_hi <= 0.2:
            return "zero"
        if per >= 80:
            return "high"
        if per >= 20:
            return "high"
        if per >= 4:
            return "mid"
        if self.win_manager.running_bet_win >= lo and remaining > 2 and random.random() < 0.45:
            return "zero"
        return "low"

    def _place_random_wild(self) -> tuple[int, int]:
        reel = random.randrange(self.config.num_reels)
        row = random.randrange(self.config.num_rows[reel])
        return reel, row

    def _bonus_floor(self) -> float:
        if self.betmode == "wildbonus":
            return 5.0 if self.criteria == "dead" else BUY_WILD_COST
        if self.betmode == "bonus":
            return 3.0 if self.criteria == "dead" else BUY_BONUS_COST
        return 10.0

    def play_hold_respin_spin(self) -> None:
        target = payout_target(self.betmode, self.criteria, self.sim)
        floor = self._bonus_floor()
        lo = floor
        hi = float(self.config.wincap)
        if target is not None and self.criteria != "wincap":
            lo = min(target, floor) if self.criteria == "dead" else max(target * 0.55, floor)
            hi = min(self.config.wincap, max(target * 1.4, lo + 1.0))
        if self.criteria == "wincap":
            lo, hi = 12000.0, 15000.0
        remaining = max(1, self.tot_fs - self.fs + 1)
        sticky = set()
        if self._conditions().get("place_bonus_wild"):
            placed = getattr(self, "bonus_wild", None)
            if placed is None:
                placed = self._place_random_wild()
                self.bonus_wild = placed
                place_wild_event(self, placed[0], placed[1])
            sticky.add(placed)
        aim = target if target is not None else floor
        if self.criteria == "dead":
            ceiling = BUY_WILD_COST if self.betmode == "wildbonus" else BUY_BONUS_COST
            aim = min(aim, ceiling - 0.1)
        last = self.fs >= self.tot_fs
        first = self.fs == 1
        locked = {key: "W" for key in sticky}
        if first and aim >= 0.4 and not self.wincap_triggered:
            slice_ = quantize_win(max(0.2, min(aim * 0.18, 40.0)))
            if self.criteria == "dead":
                slice_ = quantize_win(max(0.2, min(aim * 0.35, aim - 0.2)))
            room = self.remaining_to_wincap()
            self.paint_payout(min(slice_, room) if room > 0 else slice_, locked)
            reveal_event(self)
            self._hold_respin_loop("mid", sticky)
            return
        if last and not self.wincap_triggered:
            running = float(self.win_manager.running_bet_win)
            ceiling = None
            if self.criteria == "dead":
                ceiling = BUY_WILD_COST if self.betmode == "wildbonus" else BUY_BONUS_COST
            need = 0.0
            if self.criteria == "wincap":
                need = self.remaining_to_wincap()
            elif running + 1e-9 < floor:
                need = quantize_win((aim if aim >= floor else floor) - running)
            room = self.remaining_to_wincap()
            if need >= 0.2 and room >= 0.2:
                if ceiling is not None:
                    need = min(need, quantize_win(ceiling - 0.1 - running))
                if need >= 0.2:
                    self.paint_payout(min(need, room), locked)
                    reveal_event(self)
                    self._hold_respin_loop("mid", sticky)
                    return
        mix = self._bonus_mix_for_room(lo, hi, remaining)
        if self.win_manager.running_bet_win >= aim and remaining > 1:
            mix = "zero"
        if self.criteria == "dead":
            ceiling = BUY_WILD_COST if self.betmode == "wildbonus" else BUY_BONUS_COST
            if self.win_manager.running_bet_win >= min(aim, ceiling - 0.2) and remaining > 1:
                mix = "zero"
        self._hold_respin_body(mix=mix, sticky=sticky)

    def force_small_ways_win(self, floor: float) -> None:
        """Paint a real ways board so a short bonus still clears its floor."""
        room = self.remaining_to_wincap()
        need = quantize_win(max(0.2, min(floor - self.win_manager.running_bet_win, room or floor)))
        if need <= 0 or self.wincap_triggered:
            return
        self.paint_payout(need)
        reveal_event(self)
        self._hold_respin_loop("mid", set())
