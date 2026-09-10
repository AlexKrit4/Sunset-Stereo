import random
from copy import deepcopy

from game_calculations import GameCalculations, MAX_HOLD_RESPINS
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

    def respin_unlocked_cells(self, locked: set[tuple[int, int]]) -> None:
        """Respin cells that are not part of a held winning combination."""
        reelstrip_id = get_random_outcome(self.get_current_distribution_conditions()["reel_weights"][self.gametype])
        reelstrip = self.config.reels[reelstrip_id]
        force_wincap = bool(self.get_current_distribution_conditions().get("force_wincap"))
        for reel in range(self.config.num_reels):
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
                name = strip[random.randrange(len(strip))]
                self.board[reel][row] = self.create_symbol(name)
            if self.config.include_padding:
                self.top_symbols[reel] = self.create_symbol(strip[random.randrange(len(strip))])
                self.bottom_symbols[reel] = self.create_symbol(strip[random.randrange(len(strip))])
                self.reel_positions[reel] = random.randrange(len(reelstrip[reel]))
        self.get_special_symbols_on_board()
        self.anticipation = [0] * self.config.num_reels

    def _hold_respin_body(self) -> None:
        """One extra play: lock winning cells and respin the rest until growth stops."""
        self.draw_board()
        locked: set[tuple[int, int]] = set()
        total_cells = sum(self.config.num_rows)
        last_positive = {"totalWin": 0, "wins": []}
        for step in range(MAX_HOLD_RESPINS + 1):
            if step > 0:
                self.respin_unlocked_cells(locked)
                reveal_event(self)
            self.evaluate_ways_board(emit_events=False)
            if self.win_data["totalWin"] <= 0:
                if step > 0:
                    self.win_data = last_positive
                break
            keys = self.winning_cell_keys()
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

    def play_hold_respin_spin(self) -> None:
        """One extra play. Dead buys may redraw the extra play so the book stays under 95×."""
        if self.betmode != "bonus" or self.criteria != "dead":
            self._hold_respin_body()
            return
        for _ in range(50):
            events_len = len(self.book.events)
            running = self.win_manager.running_bet_win
            spin = self.win_manager.spin_win
            tumble = self.win_manager.tumble_win
            cap = self.wincap_triggered
            self._hold_respin_body()
            if self.win_manager.running_bet_win < 95:
                return
            self.book.events = self.book.events[:events_len]
            self.win_manager.running_bet_win = running
            self.win_manager.spin_win = spin
            self.win_manager.tumble_win = tumble
            self.wincap_triggered = cap
        self._hold_respin_zero()

    def _hold_respin_zero(self) -> None:
        """Last-resort extra play that does not recoup the 95× buy."""
        mix = ["H1", "H2", "H3", "H4", "H5", "L1", "L2", "L3", "L4", "L5"]
        for _ in range(40):
            self.draw_board(emit_event=False)
            for reel in range(self.config.num_reels):
                for row in range(self.config.num_rows[reel]):
                    self.board[reel][row] = self.create_symbol(random.choice(mix))
                if self.config.include_padding:
                    self.top_symbols[reel] = self.create_symbol(random.choice(mix))
                    self.bottom_symbols[reel] = self.create_symbol(random.choice(mix))
            self.get_special_symbols_on_board()
            self.evaluate_ways_board(emit_events=False)
            if self.win_manager.running_bet_win + self.win_data["totalWin"] < 95:
                reveal_event(self)
                self.pay_current_board()
                return
        self.draw_board(emit_event=False)
        reveal_event(self)
        self.win_data = {"totalWin": 0, "wins": []}
        self.pay_current_board()
