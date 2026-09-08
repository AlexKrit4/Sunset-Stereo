from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Sunset Stereo 6x4 ways — base plus 10 hold-respin extra plays."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()
            self.evaluate_ways_board()
            self.win_manager.update_gametype_wins(self.gametype)
            if self.check_fs_condition():
                self.run_freespin_from_base()
            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.play_hold_respin_spin()
            self.win_manager.update_gametype_wins(self.gametype)
        self.end_freespin()
