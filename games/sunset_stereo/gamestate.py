from game_override import GameStateOverride
import random


class GameState(GameStateOverride):
    """Sunset Stereo 6x4 ways — base plus 10 hold-respin extra plays."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            if self.repeat_count:
                random.seed((simulation_seed or sim) + 17 + self.repeat_count * 1_000_003)
            self.reset_book()
            self.draw_board()
            self.evaluate_ways_board()
            self.win_manager.update_gametype_wins(self.gametype)
            if self.check_fs_condition():
                self.run_freespin_from_base()
            self.evaluate_finalwin()
            self.check_repeat()
            if self.repeat and self.repeat_count >= 400:
                raise RuntimeError(
                    f"spin {sim} mode={self.betmode} criteria={self.criteria} "
                    f"stuck at win={self.final_win} after {self.repeat_count} retries"
                )
        self._apply_base_feature()
        self._apply_bonus_opening()
        self.imprint_wins()

    def _apply_base_feature(self) -> None:
        """4% main-spin feature on base/ante after the book is otherwise valid."""
        from base_feature import apply_feature_to_book, should_feature

        if self.betmode not in {"base", "scatter"}:
            return
        if not should_feature(int(getattr(self, "sim", 0))):
            return
        if self.tot_fs > 0 or any(event.get("type") == "freeSpinTrigger" for event in self.book.events):
            return
        blob = self.book.to_json()
        blob["id"] = int(getattr(self, "sim", 0))
        if not apply_feature_to_book(blob):
            return
        self.book.events = blob["events"]
        self.book.payout_multiplier = blob.get("payoutMultiplier", 0) / 100.0
        self.final_win = float(self.book.payout_multiplier)
        self.book.basegame_wins = float(blob.get("baseGameWins") or self.final_win)
        self.book.freegame_wins = 0.0

    def _apply_bonus_opening(self) -> None:
        from patch_bonus_opening import transform_book

        blob = self.book.to_json()
        blob["id"] = int(getattr(self, "sim", 0))
        if transform_book(blob):
            self.book.events = blob["events"]

    def run_freespin(self):
        self.reset_fs_spin()
        self.bonus_wild = None
        while self.fs < self.tot_fs:
            if self.wincap_triggered:
                break
            self.update_freespin()
            self.play_hold_respin_spin()
            self.win_manager.update_gametype_wins(self.gametype)
            if self.wincap_triggered:
                break
        self.end_freespin()
