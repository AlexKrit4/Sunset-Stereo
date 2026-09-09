"""Hold-and-respin extra plays for Sunset Stereo."""

from src.executables.executables import Executables

MAX_HOLD_RESPINS = 16


class GameCalculations(Executables):
    def winning_cell_keys(self) -> set[tuple[int, int]]:
        keys: set[tuple[int, int]] = set()
        for win in self.win_data.get("wins", []):
            for pos in win.get("positions", []):
                keys.add((pos["reel"], pos["row"]))
        return keys
