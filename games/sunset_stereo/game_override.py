from game_events import emit_stereo_mix
from game_executables import GameExecutables
from src.calculations.statistics import get_random_outcome


class GameStateOverride(GameExecutables):
    """Sunset Stereo overrides: wild multipliers and Stereo Mix reset."""

    def reset_book(self):
        super().reset_book()
        self.global_multiplier = 1

    def reset_fs_spin(self):
        super().reset_fs_spin()
        self.global_multiplier = 1
        emit_stereo_mix(self)

    def assign_special_sym_function(self):
        self.special_symbol_functions = {
            "W": [self.assign_mult_property],
        }

    def assign_mult_property(self, symbol) -> dict:
        """Wilds carry a 1x stub in basegame and a real multiplier in Golden Hour."""
        multiplier_value = 1
        if self.gametype == self.config.freegame_type:
            multiplier_value = get_random_outcome(
                self.get_current_distribution_conditions()["mult_values"][self.gametype]
            )
        symbol.assign_attribute({"multiplier": multiplier_value})

    def check_repeat(self):
        super().check_repeat()
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True
                return
            if win_criteria is None and self.final_win == 0:
                self.repeat = True
                return
