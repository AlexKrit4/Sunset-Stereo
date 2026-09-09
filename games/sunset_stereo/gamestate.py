from game_override import GameStateOverride
from src.events.events import reveal_event
import random


class GameState(GameStateOverride):
    """Sunset Stereo 6x4 ways — base plus 10 hold-respin extra plays."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            if self.repeat_count and self.repeat_count % 40 == 0:
                random.seed((simulation_seed or sim) + 1 + self.repeat_count * 1_000_003)
            self.reset_book()
            self.draw_board(emit_event=False)
            if self.criteria == "dead":
                self.dampen_dead_trigger_board()
            reveal_event(self)
            self.evaluate_ways_board()
            self.win_manager.update_gametype_wins(self.gametype)
            if self.check_fs_condition():
                self.run_freespin_from_base()
            self.evaluate_finalwin()
            self.check_repeat()
            if self.repeat and self.repeat_count >= 800:
                raise RuntimeError(
                    f"spin {sim} criteria={self.criteria} stuck at win={self.final_win} after {self.repeat_count} retries"
                )
        self.imprint_wins()
        if self.betmode == "bonus" and self.sim % 250 == 0:
            print(
                f"bonus sim {self.sim} {self.criteria} win={self.final_win} repeats={self.repeat_count}",
                flush=True,
            )

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            if self.wincap_triggered:
                break
            self.update_freespin()
            self.play_hold_respin_spin()
            self.win_manager.update_gametype_wins(self.gametype)
            if self.wincap_triggered:
                break
        self.end_freespin()
