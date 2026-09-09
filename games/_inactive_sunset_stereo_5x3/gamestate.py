from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Sunset Stereo simulation loop.

    Basegame is a 20-line evaluate. Golden Hour (freegame) adds Stereo Mix:
    after every winning free spin the persistent global multiplier ticks +1
    and an `updateGlobalMult` event is emitted for the frontend.
    """

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()

            self.evaluate_lines_board()

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
            self.draw_board()

            self.evaluate_lines_board()

            if self.win_manager.spin_win > 0 and not self.wincap_triggered:
                self.update_global_mult()

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
