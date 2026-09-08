import random
from copy import deepcopy

from game_calculations import GameCalculations, MAX_HOLD_RESPINS
from game_events import hold_respin_event
from src.calculations.statistics import get_random_outcome
from src.calculations.ways import Ways
from src.events.events import reveal_event


def quantize_win(value: float) -> float:
    """RGS payouts are integer cents of 0.10x (multiples of 10)."""
    return round(round(value * 10.0) / 10.0, 2)


class GameExecutables(GameCalculations):
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
        Ways.record_ways_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        Ways.emit_wayswin_events(self)

    def respin_unlocked_cells(self, locked: set[tuple[int, int]]) -> None:
        """Respin cells that are not part of a held winning combination."""
        reelstrip_id = get_random_outcome(self.get_current_distribution_conditions()["reel_weights"][self.gametype])
        reelstrip = self.config.reels[reelstrip_id]
        for reel in range(self.config.num_reels):
            strip = [symbol for symbol in reelstrip[reel] if symbol != "S"]
            if not strip:
                strip = list(reelstrip[reel])
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

    def play_hold_respin_spin(self) -> None:
        """One extra play: pay only after hold-respins stop adding winning cells."""
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
            if step < MAX_HOLD_RESPINS:
                hold_respin_event(self, locked, continuing=True)

        Ways.record_ways_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        Ways.emit_wayswin_events(self)
