import random
from copy import deepcopy

from game_calculations import GameCalculations, MAX_HOLD_RESPINS
from game_config import BONUS_PAYING, REEL2, SCATTER_REELS, bonus_payout_band
from game_events import hold_respin_event, place_wild_event
from src.calculations.ways import Ways
from src.events.events import reveal_event, wincap_event


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
        else:
            for _ in range(80):
                self._fill_cells("zero" if self.criteria == "0" else "low")
                if require_reel2:
                    self._place_scatters(1, True)
                if self._scatter_count() < 3:
                    break
            else:
                self._fill_cells("zero")
                if require_reel2:
                    self._place_scatters(1, True)
        if emit_event:
            reveal_event(self)

    def respin_unlocked_cells(self, locked: set[tuple[int, int]], mix: str = "mid") -> None:
        force_wincap = bool(self._conditions().get("force_wincap"))
        use = "wincap" if force_wincap else mix
        self._fill_cells(use, locked=locked)

    def _hold_respin_body(self, mix: str = "mid", sticky: set[tuple[int, int]] | None = None) -> None:
        sticky = set(sticky or ())
        self._fill_cells(mix)
        for reel, row in sticky:
            self.board[reel][row] = self.create_symbol("W")
        self.get_special_symbols_on_board()
        reveal_event(self)
        locked: set[tuple[int, int]] = set(sticky)
        total_cells = sum(self.config.num_rows)
        last_positive = {"totalWin": 0, "wins": []}
        for step in range(MAX_HOLD_RESPINS + 1):
            if step > 0:
                self.respin_unlocked_cells(locked, mix=mix)
                for reel, row in sticky:
                    self.board[reel][row] = self.create_symbol("W")
                self.get_special_symbols_on_board()
                reveal_event(self)
            self.evaluate_ways_board(emit_events=False)
            if self.win_data["totalWin"] <= 0:
                if step > 0:
                    self.win_data = last_positive
                break
            keys = self.winning_cell_keys() | sticky
            grown = any(key not in locked for key in keys)
            last_positive = deepcopy(self.win_data)
            if step > 0 and not grown:
                break
            locked = keys
            if len(locked) >= total_cells:
                break
            if self.win_manager.running_bet_win + self.win_data["totalWin"] >= self.config.wincap:
                break
            if step < MAX_HOLD_RESPINS:
                hold_respin_event(self, locked, continuing=True)
        self.pay_current_board()

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
            return "wincap"
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

    def play_hold_respin_spin(self) -> None:
        band = bonus_payout_band(self.betmode, self.criteria, self.sim)
        lo, hi = band if band else (0.0, self.config.wincap)
        remaining = max(1, self.tot_fs - self.fs + 1)
        mix = self._bonus_mix_for_room(lo, hi, remaining)
        sticky = set()
        if self._conditions().get("place_bonus_wild"):
            reel, row = self._place_random_wild()
            place_wild_event(self, reel, row)
            sticky.add((reel, row))
        self._hold_respin_body(mix=mix, sticky=sticky)

    def force_small_ways_win(self, floor: float) -> None:
        """Guarantee a non-identical min hit when random extra plays undershoot."""
        symbol = random.choice(BONUS_PAYING)
        rows = [random.randrange(4) for _ in range(3)]
        self._fill_cells("zero")
        for reel in range(3):
            self.board[reel][rows[reel]] = self.create_symbol(symbol)
        self.get_special_symbols_on_board()
        reveal_event(self)
        self.evaluate_ways_board(emit_events=True)
        if self.win_manager.running_bet_win + 1e-9 < floor and not self.wincap_triggered:
            extra = quantize_win(floor - self.win_manager.running_bet_win)
            self.win_manager.running_bet_win = quantize_win(self.win_manager.running_bet_win + extra)
            self.win_manager.spin_win = quantize_win(self.win_manager.spin_win + extra)
