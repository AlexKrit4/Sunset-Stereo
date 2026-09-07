"""Smoke tests for the Sunset Stereo math package."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.join(ROOT, "games", "sunset_stereo")
sys.path.insert(0, GAME)

from game_config import GameConfig  # noqa: E402


def test_config_loads_unique_reels():
    config = GameConfig()
    assert config.game_id == "sunset_stereo"
    assert config.working_name == "Sunset Stereo"
    assert config.win_type == "lines"
    assert config.num_reels == 5
    assert config.num_rows == [3, 3, 3, 3, 3]
    assert len(config.paylines) == 20
    assert config.freespin_triggers[config.basegame_type][3] == 10
    assert config.freespin_triggers[config.freegame_type][3] == 4
    assert "BR0" in config.reels
    assert "FR0" in config.reels
    assert "WCAP" in config.reels
    assert len(config.reels["BR0"]) == 5
    assert len(config.reels["BR0"][0]) >= 100


def test_bonus_mode_is_eighty_x():
    config = GameConfig()
    names = {mode.get_name(): mode.get_cost() for mode in config.bet_modes}
    assert names["base"] == 1.0
    assert names["bonus"] == 80.0


def test_scatter_not_stacked_on_base_reels():
    config = GameConfig()
    for reel in config.reels["BR0"]:
        last = -10
        for index, symbol in enumerate(reel):
            if symbol == "S":
                assert index - last >= 4
                last = index
