import random
from collections import Counter
from copy import deepcopy

from game_calculations import GameCalculations, MAX_HOLD_RESPINS
from game_config import BONUS_PAYING, bonus_payout_band
from game_events import hold_respin_event
from src.calculations.statistics import get_random_outcome
from src.calculations.ways import Ways
from src.events.events import reveal_event, wincap_event


def quantize_win(value: float) -> float:
    """RGS payouts are integer cents of 0.10x (multiples of 10)."""
    return round(round(value * 10.0) / 10.0, 2)


class GameExecutables(GameCalculations):
    def remaining_to_wincap(self) -> float:
        """How much of the 15000x ceiling is still unpaid in this book."""
        room = self.config.wincap - self.win_manager.running_bet_win
        return quantize_win(max(0.0, room))

    def clamp_win_data_to_ceiling(self) -> bool:
        """Keep the real board, but never pay past the wincap. Returns True if this hit the cap."""
        room = self.remaining_to_wincap()
        total = float(self.win_data.get("totalWin", 0) or 0)
        crossed = self.win_manager.running_bet_win + total >= self.config.wincap and (
            total > 0 or self.win_manager.running_bet_win >= self.config.wincap
        )
        if total > room:
            self.win_data["totalWin"] = room
        return crossed

    def pay_current_board(self) -> None:
        """Record and emit the current board win, then lock the book if the ceiling was hit."""
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
        """Populate win-data, optionally record wins and transmit events."""
        self.win_data = Ways.get_ways_data(self.config, self.board)
        self.win_data["totalWin"] = quantize_win(self.win_data.get("totalWin", 0))
        for win in self.win_data.get("wins", []):
            win["win"] = quantize_win(win.get("win", 0))
            if "meta" in win and "winWithoutMult" in win["meta"]:
                win["meta"]["winWithoutMult"] = quantize_win(win["meta"]["winWithoutMult"])
        if not emit_events:
            return
        self.pay_current_board()

    def _pick_paying(self, bias: dict[str, int] | None = None) -> str:
        mix = bias or {name: 1 for name in BONUS_PAYING}
        names = list(mix)
        weights = [mix[name] for name in names]
        return random.choices(names, weights=weights, k=1)[0]

    def fill_mixed_board(self, bias: dict[str, int] | None = None, avoid_scripted: bool = True) -> None:
        """Independent cells from the full alphabet — not stacked strip windows."""
        self.reelstrip_id = "FR0"
        self.reelstrip = self.config.reels["FR0"]
        for _ in range(24):
            self.refresh_special_syms()
            board = []
            top_symbols = []
            bottom_symbols = []
            reel_positions = []
            for reel in range(self.config.num_reels):
                column = [self.create_symbol(self._pick_paying(bias)) for _ in range(self.config.num_rows[reel])]
                board.append(column)
                top_symbols.append(self.create_symbol(self._pick_paying(bias)))
                bottom_symbols.append(self.create_symbol(self._pick_paying(bias)))
                reel_positions.append(random.randrange(len(self.reelstrip[reel])))
            self.board = board
            self.top_symbols = top_symbols
            self.bottom_symbols = bottom_symbols
            self.reel_positions = reel_positions
            self.padding_position = [
                (reel_positions[reel] + self.config.num_rows[reel] + 1) % len(self.reelstrip[reel])
                for reel in range(self.config.num_reels)
            ]
            self.anticipation = [0] * self.config.num_reels
            self.get_special_symbols_on_board()
            if not avoid_scripted or not self._left_reels_scripted():
                return

    def _left_reels_scripted(self) -> bool:
        """True when the first three reels are dominated by the same symbol."""
        modes = []
        for reel in range(3):
            names = [self.board[reel][row].name for row in range(self.config.num_rows[reel])]
            name, count = Counter(names).most_common(1)[0]
            modes.append(name if count >= 3 else None)
        return bool(modes[0]) and modes[0] == modes[1] == modes[2]

    def respin_unlocked_cells(self, locked: set[tuple[int, int]], bias: dict[str, int] | None = None) -> None:
        """Respin cells that are not part of a held winning combination."""
        bonus_mix = self.betmode == "bonus" and self.criteria != "wincap"
        if not bonus_mix:
            reelstrip_id = get_random_outcome(self.get_current_distribution_conditions()["reel_weights"][self.gametype])
            reelstrip = self.config.reels[reelstrip_id]
            force_wincap = bool(self.get_current_distribution_conditions().get("force_wincap"))
        for reel in range(self.config.num_reels):
            if not bonus_mix:
                strip = [symbol for symbol in reelstrip[reel] if symbol != "S"]
                if not strip:
                    strip = list(reelstrip[reel])
                if force_wincap:
                    highs = [symbol for symbol in strip if symbol in {"H1", "H2"}]
                    if highs:
                        strip = highs + strip
            for row in range(self.config.num_rows[reel]):
                if (reel, row) in locked:
                    continue
                name = self._pick_paying(bias) if bonus_mix else strip[random.randrange(len(strip))]
                self.board[reel][row] = self.create_symbol(name)
            if self.config.include_padding:
                pad_name = self._pick_paying(bias) if bonus_mix else strip[random.randrange(len(strip))]
                self.top_symbols[reel] = self.create_symbol(pad_name)
                pad_name = self._pick_paying(bias) if bonus_mix else strip[random.randrange(len(strip))]
                self.bottom_symbols[reel] = self.create_symbol(pad_name)
                if not bonus_mix:
                    self.reel_positions[reel] = random.randrange(len(reelstrip[reel]))
        self.get_special_symbols_on_board()
        self.anticipation = [0] * self.config.num_reels

    def _trim_locks(self, locked: set[tuple[int, int]], max_per_reel: int) -> set[tuple[int, int]]:
        if max_per_reel >= 4:
            return locked
        kept: set[tuple[int, int]] = set()
        by_reel: dict[int, list[tuple[int, int]]] = {}
        for reel, row in locked:
            by_reel.setdefault(reel, []).append((reel, row))
        for reel, cells in by_reel.items():
            random.shuffle(cells)
            kept.update(cells[:max_per_reel])
        return kept

    def _hold_respin_body(
        self,
        max_steps: int | None = None,
        max_locked_per_reel: int = 4,
        bias: dict[str, int] | None = None,
        avoid_scripted: bool = False,
        extra_play_cap: float | None = None,
    ) -> None:
        """One extra play: pay only after hold-respins stop adding winning cells."""
        steps = MAX_HOLD_RESPINS if max_steps is None else max_steps
        if self.betmode == "bonus" and self.criteria != "wincap":
            self.fill_mixed_board(bias=bias, avoid_scripted=avoid_scripted)
            reveal_event(self)
        else:
            self.draw_board()
        locked: set[tuple[int, int]] = set()
        total_cells = sum(self.config.num_rows)
        last_positive = {"totalWin": 0, "wins": []}
        for step in range(steps + 1):
            if step > 0:
                self.respin_unlocked_cells(locked, bias=bias)
                reveal_event(self)
            self.evaluate_ways_board(emit_events=False)
            if self.win_data["totalWin"] <= 0:
                if step > 0:
                    self.win_data = last_positive
                break
            keys = self.winning_cell_keys()
            grown = any(key not in locked for key in keys)
            last_positive = deepcopy(self.win_data)
            locked = self._trim_locks(keys, max_locked_per_reel)
            if extra_play_cap is not None and self.win_data["totalWin"] >= extra_play_cap:
                break
            if step > 0 and not grown:
                break
            if len(locked) >= total_cells:
                break
            if self.win_manager.running_bet_win + self.win_data["totalWin"] >= self.config.wincap:
                break
            if step < steps:
                hold_respin_event(self, locked, continuing=True)

        self.pay_current_board()

    def _intensity(self, need_lo: float, need_hi: float) -> tuple[int, int, dict[str, int] | None, bool]:
        """Hold depth, lock cap, symbol bias, and whether to avoid a scripted left-three."""
        mid = (max(0.0, need_lo) + max(0.0, need_hi)) / 2.0
        if need_hi <= 0.05:
            return 0, 1, {name: 1 for name in BONUS_PAYING}, True
        if mid < 2:
            return 1, 2, None, True
        if mid < 12:
            return 2, 2, None, True
        if mid < 40:
            return 3, 2, None, True
        if mid < 120:
            return 5, 3, {"H1": 3, "H2": 3, "H3": 2, "H4": 2, "H5": 2, "L1": 1, "L2": 1, "L3": 1, "L4": 1, "L5": 1}, False
        if mid < 400:
            return 8, 4, {"H1": 6, "H2": 4, "H3": 2, "H4": 1, "H5": 1, "L1": 1, "L2": 1, "L3": 1, "L4": 1, "L5": 1}, False
        return 12, 4, {"H1": 10, "H2": 5, "H3": 2, "H4": 1, "H5": 1, "L1": 1, "L2": 1, "L3": 1, "L4": 1, "L5": 1}, False

    def _snapshot_extra_play(self) -> tuple:
        return (
            len(self.book.events),
            self.win_manager.running_bet_win,
            self.win_manager.spin_win,
            self.win_manager.tumble_win,
            self.wincap_triggered,
        )

    def _restore_extra_play(self, snap: tuple) -> None:
        events_len, running, spin, tumble, cap = snap
        self.book.events = self.book.events[:events_len]
        self.win_manager.running_bet_win = running
        self.win_manager.spin_win = spin
        self.win_manager.tumble_win = tumble
        self.wincap_triggered = cap

    def play_hold_respin_spin(self) -> None:
        """One extra play: pay only after hold-respins stop adding winning cells."""
        if self.betmode != "bonus" or self.criteria == "wincap":
            self._hold_respin_body()
            return

        band = bonus_payout_band(self.criteria, self.sim)
        lo, hi = band if band else (0.0, 15000.0)
        left = max(1, int(self.tot_fs) - int(self.fs) + 1)
        running = self.win_manager.running_bet_win
        room_lo = lo - running
        room_hi = hi - running - 1e-9
        # Leave headroom for later extra plays; never overshoot the band.
        need_lo = max(0.0, room_lo - 900.0 * (left - 1))
        need_hi = max(0.0, room_hi)
        if left == 1:
            need_lo = max(0.0, room_lo)

        steps, lock_cap, bias, avoid = self._intensity(need_lo, need_hi)
        extra_cap = need_hi if need_hi > 0 else 0.05
        if extra_cap < 0.2:
            extra_cap = 0.05

        for attempt in range(40):
            snap = self._snapshot_extra_play()
            if attempt > 12 and need_lo > 0:
                steps = min(MAX_HOLD_RESPINS, steps + 2)
                lock_cap = 4
                avoid = False
            self._hold_respin_body(
                max_steps=steps,
                max_locked_per_reel=lock_cap,
                bias=bias,
                avoid_scripted=avoid,
                extra_play_cap=extra_cap if extra_cap < 8000 else None,
            )
            added = self.win_manager.running_bet_win - snap[1]
            total = self.win_manager.running_bet_win
            if total >= hi:
                self._restore_extra_play(snap)
                steps = max(0, steps - 1)
                lock_cap = min(lock_cap, 2)
                extra_cap = max(0.05, extra_cap * 0.6)
                continue
            if left == 1 and total < lo:
                self._restore_extra_play(snap)
                continue
            if added > extra_cap * 1.8 and extra_cap < 500:
                self._restore_extra_play(snap)
                continue
            return

        snap = self._snapshot_extra_play()
        self.fill_mixed_board(avoid_scripted=True)
        reveal_event(self)
        self.evaluate_ways_board(emit_events=False)
        if self.win_manager.running_bet_win + self.win_data["totalWin"] >= hi:
            self._restore_extra_play(snap)
            self.fill_mixed_board(avoid_scripted=True)
            reveal_event(self)
            self.win_data = {"totalWin": 0, "wins": []}
        self.pay_current_board()
