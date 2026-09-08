"""Smoke tests for the Sunset Stereo 6x4 ways math package."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = os.path.join(ROOT, "games", "sunset_stereo")
sys.path.insert(0, GAME)

from game_config import GameConfig  # noqa: E402


def test_config_loads_six_by_four_ways():
    config = GameConfig()
    assert config.game_id == "sunset_stereo"
    assert config.working_name == "Sunset Stereo"
    assert config.win_type == "ways"
    assert config.num_reels == 6
    assert config.num_rows == [4, 4, 4, 4, 4, 4]
    assert config.paylines == {}
    assert config.freespin_triggers[config.basegame_type] == {}
    assert config.special_symbols["wild"] == []
    assert config.special_symbols["scatter"] == ["S"]
    assert "BR0" in config.reels
    assert "FR0" not in config.reels
    assert len(config.reels["BR0"]) == 6
    assert len(config.reels["BR0"][0]) >= 100
    assert (6, "H1") in config.paytable
    assert (3, "H5") in config.paytable


def test_only_base_mode():
    config = GameConfig()
    names = {mode.get_name(): mode.get_cost() for mode in config.bet_modes}
    assert names == {"base": 1.0}


def test_scatter_only_on_inner_reels_and_not_stacked():
    config = GameConfig()
    strips = config.reels["BR0"]
    assert "S" not in strips[0]
    assert "S" not in strips[5]
    for reel_index in (1, 2, 3, 4):
        reel = strips[reel_index]
        assert reel.count("S") >= 1
        last = -10
        for index, symbol in enumerate(reel):
            if symbol == "S":
                assert index - last >= 4
                last = index
    for reel in strips:
        assert "W" not in reel


def test_one_base_spin_is_six_by_four_ways():
    from gamestate import GameState

    config = GameConfig()
    state = GameState(config)
    state.betmode = "base"
    state.criteria = "basegame"
    state.run_spin(7)
    book = state.book.to_json()
    reveal = book["events"][0]
    assert reveal["type"] == "reveal"
    assert len(reveal["board"]) == 6
    assert all(len(col) == 6 for col in reveal["board"])
    assert book["events"][-1]["type"] == "finalWin"
    assert not any(event["type"].startswith("freeSpin") for event in book["events"])
