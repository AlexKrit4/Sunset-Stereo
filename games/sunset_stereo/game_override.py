from game_config import bonus_payout_band
from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """No wild multipliers. Bonus dead books may pay 0. Recoup is 95× to just under cap."""

    def assign_special_sym_function(self):
        self.special_symbol_functions = {}

    def check_repeat(self):
        super().check_repeat()
        if self.repeat is True:
            return
        win_criteria = self.get_current_betmode_distributions().get_win_criteria()
        if self.betmode == "bonus":
            band = bonus_payout_band(self.criteria, self.sim)
            if band is not None:
                lo, hi = band
                if self.criteria == "wincap":
                    if self.final_win != self.config.wincap:
                        self.repeat = True
                    return
                if not (lo <= self.final_win < hi):
                    self.repeat = True
                return
        if self.criteria == "dead":
            if not (0 <= self.final_win < 95):
                self.repeat = True
            return
        if self.criteria == "recoup":
            if not (95 <= self.final_win < self.config.wincap):
                self.repeat = True
            return
        if win_criteria is not None and self.final_win != win_criteria:
            self.repeat = True
            return
        if win_criteria is None and self.final_win == 0 and self.criteria != "freegame":
            self.repeat = True
            return
