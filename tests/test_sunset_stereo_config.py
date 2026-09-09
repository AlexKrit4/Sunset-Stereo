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
    assert config.freespin_triggers[config.basegame_type] == {3: 10, 4: 10}
    assert config.freespin_triggers[config.freegame_type] == {}
    assert config.special_symbols["wild"] == []
    assert config.special_symbols["scatter"] == ["S"]
    assert "BR0" in config.reels
    assert "FR0" in config.reels
    assert "FR_DEAD" in config.reels
    assert "FR_RECOUP" in config.reels
    assert "FR_WCAP" in config.reels
    assert len(config.reels["BR0"]) == 6
    assert len(config.reels["FR0"]) == 6
    assert len(config.reels["BR0"][0]) >= 100
    for extra in ("FR_DEAD", "FR_RECOUP", "FR_WCAP"):
        assert len(config.reels[extra]) == 6
        for reel in config.reels[extra]:
            assert "S" not in reel
            assert "W" not in reel
    assert config.wincap == 15000.0
    assert config.rtp == 0.95
    assert (6, "H1") in config.paytable
    assert config.paytable[(3, "H1")] == 0.9
    assert (3, "H5") in config.paytable
    assert all(round(value, 1) == value for value in config.paytable.values())


def test_base_and_buy_bonus_modes():
    from game_config import BUY_BONUS_COST, BUY_BONUS_DEAD, BUY_BONUS_RECOUP, BUY_BONUS_WINCAP

    config = GameConfig()
    names = {mode.get_name(): mode.get_cost() for mode in config.bet_modes}
    assert names == {"base": 1.0, "bonus": BUY_BONUS_COST}
    assert BUY_BONUS_COST == 95.0
    base = next(mode for mode in config.bet_modes if mode.get_name() == "base")
    bonus = next(mode for mode in config.bet_modes if mode.get_name() == "bonus")
    assert base.get_buybonus() is False
    assert base.get_feature() is True
    assert bonus.get_buybonus() is True
    assert bonus.get_feature() is False
    assert [dist.get_criteria() for dist in base.get_distributions()] == ["wincap", "freegame", "0", "basegame"]
    amounts = {dist.get_criteria(): dist.get_fixed_amt() for dist in bonus.get_distributions()}
    assert amounts == {"wincap": BUY_BONUS_WINCAP, "dead": BUY_BONUS_DEAD, "recoup": BUY_BONUS_RECOUP}
    assert BUY_BONUS_DEAD + BUY_BONUS_RECOUP + BUY_BONUS_WINCAP == 50_000


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
    for reel in config.reels["FR0"]:
        assert "S" not in reel
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
    assert not any(event["type"] == "holdRespin" for event in book["events"])


def test_three_scatters_start_ten_hold_respin_extra_plays():
    from gamestate import GameState

    config = GameConfig()
    state = GameState(config)
    state.betmode = "base"
    state.criteria = "freegame"
    state.run_spin(3)
    book = state.book.to_json()
    types = [event["type"] for event in book["events"]]
    assert "freeSpinTrigger" in types
    trigger = next(event for event in book["events"] if event["type"] == "freeSpinTrigger")
    assert trigger["totalFs"] == 10
    assert types.count("updateFreeSpin") == 10
    assert "freeSpinEnd" in types
    assert "freeSpinRetrigger" not in types
    assert types.count("reveal") >= 11
    extra_reveals = [event for event in book["events"] if event["type"] == "reveal" and event.get("gameType") == "freegame"]
    assert extra_reveals
    for reveal in extra_reveals:
        for col in reveal["board"]:
            names = [cell["name"] if isinstance(cell, dict) else cell for cell in col]
            assert "S" not in names[1:-1]


def test_hold_respin_stops_before_paying_an_extra_play():
    from gamestate import GameState

    config = GameConfig()
    for sim in range(80):
        state = GameState(config)
        state.betmode = "base"
        state.criteria = "freegame"
        state.run_spin(sim)
        events = state.book.to_json()["events"]
        if any(event["type"] == "holdRespin" for event in events):
            types = [event["type"] for event in events]
            first_hold = types.index("holdRespin")
            assert types[first_hold - 1] == "reveal"
            after = types[first_hold + 1 :]
            assert "reveal" in after
            assert "winInfo" in after or "setWin" in after
            return
    raise AssertionError("expected at least one hold-respin extra play in 80 forced bonus books")


def test_wincap_is_a_hard_ceiling_and_stops_the_book():
    from gamestate import GameState

    GameConfig._instance = None
    config = GameConfig()
    config.wincap = 8.0
    state = GameState(config)
    state.win_manager.max_allowed_win = 8.0
    state.betmode = "base"
    state.criteria = "freegame"
    hit = False
    for sim in range(40):
        state.run_spin(sim)
        assert state.final_win <= 8.0 + 1e-9
        events = state.book.to_json()["events"]
        types = [event["type"] for event in events]
        if "wincap" in types:
            hit = True
            assert state.final_win == 8.0
            wincap_at = types.index("wincap")
            assert "reveal" not in types[wincap_at + 1 :]
            assert types[-1] == "finalWin"
            final = next(event for event in events if event["type"] == "finalWin")
            assert final["amount"] == 800
            break
    GameConfig._instance = None
    assert hit, "expected a bonus book to hit the lowered 8x ceiling"


def _bonus_book(criteria: str, sim: int):
    from gamestate import GameState

    GameConfig._instance = None
    config = GameConfig()
    state = GameState(config)
    state.betmode = "bonus"
    state.criteria = criteria
    state.run_spin(sim)
    return state, state.book.to_json()


def test_buy_bonus_always_starts_ten_extra_plays_from_three_scatters():
    state, book = _bonus_book("dead", 11)
    types = [event["type"] for event in book["events"]]
    reveal = book["events"][0]
    assert reveal["type"] == "reveal"
    assert reveal["gameType"] == "basegame"
    suns = 0
    for col in reveal["board"]:
        names = [cell["name"] if isinstance(cell, dict) else cell for cell in col]
        suns += names[1:-1].count("S")
    assert suns == 3
    assert "freeSpinTrigger" in types
    trigger = next(event for event in book["events"] if event["type"] == "freeSpinTrigger")
    assert trigger["totalFs"] == 10
    assert types.count("updateFreeSpin") == 10
    assert "freeSpinEnd" in types
    assert types[-1] == "finalWin"
    assert state.final_win < 95


def test_buy_bonus_recoup_pays_at_least_the_95x_cost():
    state, book = _bonus_book("recoup", 21)
    assert 95 <= state.final_win < 15000
    types = [event["type"] for event in book["events"]]
    assert types.count("updateFreeSpin") == 10
    extra = [event for event in book["events"] if event["type"] == "reveal" and event.get("gameType") == "freegame"]
    assert extra
    boards = []
    for reveal in extra:
        board = tuple(
            tuple(cell["name"] if isinstance(cell, dict) else cell for cell in col[1:-1])
            for col in reveal["board"]
        )
        boards.append(board)
        for col in reveal["board"]:
            names = [cell["name"] if isinstance(cell, dict) else cell for cell in col]
            assert "S" not in names[1:-1]
    assert len(set(boards)) > 1


def test_buy_bonus_wincap_hits_the_15000x_ceiling():
    state, book = _bonus_book("wincap", 3)
    assert state.final_win == 15000
    types = [event["type"] for event in book["events"]]
    assert "wincap" in types
    final = next(event for event in book["events"] if event["type"] == "finalWin")
    assert final["amount"] == 1_500_000


def test_bonus_lookup_weights_lock_75_25_and_rtp():
    from weight_bonus import assign_weights, lut_stats

    rows = []
    book_id = 0
    for cents in [0, 10, 4000, 8000, 9400] * 8:
        rows.append((book_id, 1, cents))
        book_id += 1
    for cents in [9500, 12000, 40000, 180000, 900000] * 3:
        rows.append((book_id, 1, cents))
        book_id += 1
    rows.append((book_id, 1, 1_500_000))
    weighted = assign_weights(rows)
    stats = lut_stats(weighted)
    assert abs(stats["dead_mass"] - 0.75) < 0.01
    assert abs(stats["recoup_mass"] - 0.25) < 0.01
    assert 0.94 <= stats["rtp"] <= 0.96
    assert stats["wincap_mass"] < 0.001
    assert stats["hit_rate"] >= 1 / 50

