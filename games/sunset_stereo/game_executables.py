from game_calculations import GameCalculations
from src.calculations.ways import Ways
from src.events.events import reveal_event


class GameExecutables(GameCalculations):
    def draw_board(self, emit_event: bool = True, trigger_symbol: str = "scatter") -> None:
        """No free-spin reject loop — scatter is tease-only."""
        self.create_board_reelstrips()
        if emit_event:
            reveal_event(self)

    def evaluate_ways_board(self):
        """Populate win-data, record wins, transmit events."""
        self.win_data = Ways.get_ways_data(self.config, self.board)
        Ways.record_ways_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        Ways.emit_wayswin_events(self)
