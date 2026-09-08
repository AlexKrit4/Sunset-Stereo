from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Sunset Stereo 6x4 ways — basegame only, no Golden Hour."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()
            self.evaluate_ways_board()
            self.win_manager.update_gametype_wins(self.gametype)
            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        """Unused: production game has no extra-spin round."""
        return
