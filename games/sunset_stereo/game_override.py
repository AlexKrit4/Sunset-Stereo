from game_config import (
    BUY_BONUS_COST,
    BUY_BONUS_MIN,
    BUY_WILD_COST,
    BUY_WILD_MIN,
    NATURAL_BONUS_MIN,
    bonus_payout_band,
)
from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    def assign_special_sym_function(self):
        self.special_symbol_functions = {}

    def _band(self) -> tuple[float, float] | None:
        return bonus_payout_band(self.betmode, self.criteria, self.sim)

    def _triggered_bonus(self) -> bool:
        return self.tot_fs > 0 or any(event.get("type") == "freeSpinTrigger" for event in self.book.events)

    def check_repeat(self):
        super().check_repeat()
        if self.repeat is True:
            return
        win = float(self.final_win)
        band = self._band()
        if self.criteria == "dead":
            floor = BUY_WILD_MIN if self.betmode == "wildbonus" else BUY_BONUS_MIN
            ceiling = BUY_WILD_COST if self.betmode == "wildbonus" else BUY_BONUS_COST
            if not (floor - 1e-9 <= win < ceiling):
                self.repeat = True
            elif band and not (band[0] - 1e-6 <= win < band[1] + 1e-6) and self.repeat_count < 80:
                self.repeat = True
            return
        if self.criteria == "recoup":
            floor = BUY_WILD_COST if self.betmode == "wildbonus" else BUY_BONUS_COST
            if not (floor - 1e-9 <= win < self.config.wincap):
                self.repeat = True
            elif band and not (band[0] - 1e-6 <= win < band[1] + 1e-6) and self.repeat_count < 80:
                self.repeat = True
            return
        if self.criteria in {"freegame", "freegame4"}:
            floor = min(NATURAL_BONUS_MIN, float(self.config.wincap))
            if not self._triggered_bonus() or win + 1e-9 < floor:
                self.repeat = True
            elif band and not (band[0] - 1e-6 <= win < band[1] + 1e-6) and self.repeat_count < 60:
                self.repeat = True
            return
        if self.criteria == "0":
            if win != 0 or self._triggered_bonus():
                self.repeat = True
            return
        if self.criteria == "basegame":
            if win <= 0 or self._triggered_bonus():
                self.repeat = True
            return
        win_criteria = self.get_current_betmode_distributions().get_win_criteria()
        if win_criteria is not None and abs(win - float(win_criteria)) > 1e-9:
            self.repeat = True
            return
        if win_criteria is None and win == 0 and self.criteria not in {"freegame", "freegame4", "0"}:
            self.repeat = True
