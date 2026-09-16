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
    assert config.special_symbols["wild"] == ["W"]
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
    from game_config import BUY_BONUS_COST, BUY_WILD_COST, SCATTER_COST

    config = GameConfig()
    names = {mode.get_name(): mode.get_cost() for mode in config.bet_modes}
    assert names == {
        "base": 1.0,
        "scatter": SCATTER_COST,
        "bonus": BUY_BONUS_COST,
        "wildbonus": BUY_WILD_COST,
    }
    base = next(mode for mode in config.bet_modes if mode.get_name() == "base")
    scatter = next(mode for mode in config.bet_modes if mode.get_name() == "scatter")
    bonus = next(mode for mode in config.bet_modes if mode.get_name() == "bonus")
    wild = next(mode for mode in config.bet_modes if mode.get_name() == "wildbonus")
    assert base.get_buybonus() is False
    assert scatter.get_feature() is True
    assert bonus.get_buybonus() is True
    assert wild.get_buybonus() is True
    assert [dist.get_criteria() for dist in base.get_distributions()] == [
        "wincap",
        "freegame4",
        "freegame",
        "0",
        "basegame",
    ]
    assert [dist.get_criteria() for dist in scatter.get_distributions()] == [
        "wincap",
        "freegame4",
        "freegame",
        "0",
        "basegame",
    ]
    amounts = {dist.get_criteria(): dist.get_fixed_amt() for dist in bonus.get_distributions()}
    assert amounts["dead"] + amounts["recoup"] + amounts["wincap"] == 250_000
    wild_amt = {dist.get_criteria(): dist.get_fixed_amt() for dist in wild.get_distributions()}
    assert wild_amt["dead"] + wild_amt["recoup"] + wild_amt["wincap"] == 250_000


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
    assert 3 <= state.final_win < 95


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


def test_bonus_lookup_weights_lock_diversity_and_rtp():
    from weight_modes import assign_weights, lut_stats

    rows = []
    book_id = 0
    for cents in [0] * 40:
        rows.append((book_id, 1, cents))
        book_id += 1
    for cents in [20, 80, 150, 400, 900, 1400, 3500, 8000] * 8:
        rows.append((book_id, 1, cents))
        book_id += 1
    for cents in [12000, 25000, 80000, 160000, 400000, 900000] * 4:
        rows.append((book_id, 1, cents))
        book_id += 1
    rows.append((book_id, 1, 1_500_000))
    weighted = assign_weights(rows, "base")
    stats = lut_stats(weighted, "base")
    assert 0.93 <= stats["rtp"] <= 0.97
    assert stats["hit_rate"] >= 1 / 50
    assert stats["unique_payouts"] >= 15
    assert stats["peak_range_rtp"] < 0.45


def test_bonus_lut_writer_uses_unix_newlines(tmp_path):
    from weight_modes import write_lut

    path = tmp_path / "lookUpTable_bonus_0.csv"
    write_lut(str(path), [(0, 10, 0), (1, 20, 9500)])
    raw = path.read_bytes()
    assert b"\r" not in raw
    assert raw == b"0,10,0\n1,20,9500\n"


def test_buy_bonus_extra_plays_mix_left_reels():
    for sim in (11, 17, 23, 29, 41, 47):
        _state, book = _bonus_book("dead", sim)
        extra = [event for event in book["events"] if event["type"] == "reveal" and event.get("gameType") == "freegame"]
        assert extra
        reveal = extra[0]
        visible = []
        for reel in range(6):
            names = [
                cell["name"] if isinstance(cell, dict) else cell
                for cell in reveal["board"][reel][1:-1]
            ]
            visible.extend(names)
            assert "S" not in names
        assert len(set(visible)) >= 4


def test_buy_bonus_hold_respin_grows_before_paying():
    found = False
    for sim in range(40):
        _state, book = _bonus_book("recoup", sim)
        types = [event["type"] for event in book["events"]]
        if "holdRespin" not in types:
            continue
        found = True
        first = types.index("holdRespin")
        assert types[first - 1] == "reveal"
        after = types[first + 1 :]
        assert "reveal" in after
        assert after.index("reveal") < after.index("winInfo") if "winInfo" in after else True
        break
    assert found, "expected a buy-bonus extra play to hold and respin"


def _mode_book(mode: str, criteria: str, sim: int):
    from gamestate import GameState

    GameConfig._instance = None
    config = GameConfig()
    state = GameState(config)
    state.betmode = mode
    state.criteria = criteria
    state.run_spin(sim)
    return state, state.book.to_json()


def test_zero_spins_are_not_cloned():
    from ways_paint import is_stacked_column_board, visible_ways_win

    boards = []
    for sim in range(12):
        state, book = _mode_book("base", "0", sim)
        reveal = book["events"][0]
        visible = tuple(
            tuple(cell["name"] if isinstance(cell, dict) else cell for cell in col[1:-1])
            for col in reveal["board"]
        )
        boards.append(visible)
        names = [list(col) for col in visible]
        assert book["payoutMultiplier"] == 0
        assert state.final_win == 0
        assert visible_ways_win(names) == 0
        assert not is_stacked_column_board(names)
        for col in names:
            paying = [name for name in col if name not in {"S", "W"}]
            assert len(set(paying)) >= 2
    assert len(set(boards)) == len(boards)


def test_mixed_dead_boards_never_pay_or_stack():
    import random

    from ways_paint import is_stacked_column_board, paint_mixed_dead, visible_ways_win

    rng = random.Random(20260916)
    boards = []
    for i in range(80):
        locked = {(1, i % 4): "S"} if i % 5 == 0 else {}
        board = paint_mixed_dead(rng, locked)
        boards.append(tuple(tuple(col) for col in board))
        assert visible_ways_win(board) == 0
        assert not is_stacked_column_board(board)
        for reel, col in enumerate(board):
            paying = [name for name in col if name not in {"S", "W"}]
            assert len(set(paying)) >= 2
            if locked and reel == 1:
                assert board[1][i % 4] == "S"
    assert len(set(boards)) == len(boards)


def test_scatter_ante_locks_sun_on_reel_two():
    for criteria, sim in (("0", 4), ("basegame", 9), ("freegame", 3)):
        state, book = _mode_book("scatter", criteria, sim)
        reveal = book["events"][0]
        names = [cell["name"] if isinstance(cell, dict) else cell for cell in reveal["board"][1][1:-1]]
        assert "S" in names
        if criteria == "freegame":
            assert state.final_win >= 10


def test_four_scatter_buy_places_a_locked_wild():
    state, book = _mode_book("wildbonus", "dead", 15)
    types = [event["type"] for event in book["events"]]
    assert "placeWild" in types
    assert types.count("updateFreeSpin") == 10
    suns = 0
    reveal = book["events"][0]
    for col in reveal["board"]:
        names = [cell["name"] if isinstance(cell, dict) else cell for cell in col]
        suns += names[1:-1].count("S")
    assert suns == 4
    assert state.final_win >= 5
    wild = next(event for event in book["events"] if event["type"] == "placeWild")
    assert 0 <= wild["reel"] <= 5
    assert 1 <= wild["row"] <= 4


def test_hit_fillers_are_not_the_winning_symbol():
    import random

    from ways_paint import filler_column_reels, paint_hit_fillers, visible_ways_win

    rng = random.Random(77)
    occupied = {(0, 0): "L2", (1, 1): "L2", (2, 2): "L2"}
    board = paint_hit_fillers(occupied, rng)
    assert visible_ways_win(board) == 0.2
    assert not filler_column_reels(board, occupied)
    for reel, col in enumerate(board):
        for row, name in enumerate(col):
            if (reel, row) not in occupied:
                assert name != "L2"
                assert name != "W"


def test_painted_basegame_hits_are_not_cloned_payouts():
    from gamestate import GameState
    from ways_paint import payout_target

    GameConfig._instance = None
    config = GameConfig()
    payouts = []
    boards = []
    for sim in range(80):
        state = GameState(config)
        state.betmode = "base"
        state.criteria = "basegame"
        state.run_spin(sim)
        payouts.append(round(state.final_win, 1))
        reveal = state.book.to_json()["events"][0]
        boards.append(
            tuple(tuple(cell["name"] if isinstance(cell, dict) else cell for cell in col[1:-1]) for col in reveal["board"])
        )
        assert state.final_win > 0
        target = payout_target("base", "basegame", sim)
        if target:
            from ways_paint import plan_payout, planned_tenths, from_tenths

            planned = from_tenths(planned_tenths(plan_payout(target)))
            assert abs(state.final_win - planned) <= max(0.6, 0.2 * planned)
            win = next(event for event in state.book.to_json()["events"] if event["type"] == "winInfo")
            occupied = {}
            keep = set()
            for item in win["wins"]:
                keep.add(item["symbol"])
                for pos in item["positions"]:
                    row = pos["row"] - 1
                    if 0 <= row < 4:
                        occupied[(pos["reel"], row)] = item["symbol"]
            visible_names = [list(col) for col in boards[-1]]
            from ways_paint import filler_column_reels, visible_ways_win

            assert not filler_column_reels(visible_names, occupied)
            for reel, col in enumerate(visible_names):
                for row, name in enumerate(col):
                    if (reel, row) not in occupied and name not in {"S", "W"}:
                        assert name not in keep
            assert abs(visible_ways_win(visible_names) - win["totalWin"] / 100.0) < 0.05
    assert len(set(boards)) == len(boards)
    assert len(set(payouts)) >= 20


def test_weighter_spreads_rtp_across_ranges():
    from weight_modes import assign_weights, lut_stats

    rows = []
    book_id = 0
    for cents in [0] * 200:
        rows.append((book_id, 1, cents))
        book_id += 1
    for cents in range(20, 200, 10):
        rows.append((book_id, 1, cents))
        book_id += 1
    for cents in [400, 900, 1400, 3500, 8000, 16000, 45000, 120000, 350000, 900000] * 3:
        rows.append((book_id, 1, cents))
        book_id += 1
    rows.append((book_id, 1, 1_500_000))
    weighted = assign_weights(rows, "base")
    stats = lut_stats(weighted, "base")
    assert 0.93 <= stats["rtp"] <= 0.97
    assert stats["peak_range_rtp"] < 0.45
    assert stats["hit_rate"] >= 1 / 50


def test_natural_three_scatter_bonus_pays_at_least_10x():
    state, book = _mode_book("base", "freegame", 8)
    assert state.final_win >= 10
    types = [event["type"] for event in book["events"]]
    assert "freeSpinTrigger" in types
    extra = [event for event in book["events"] if event["type"] == "reveal" and event.get("gameType") == "freegame"]
    boards = [
        tuple(tuple(cell["name"] if isinstance(cell, dict) else cell for cell in col[1:-1]) for col in reveal["board"])
        for reveal in extra
    ]
    assert len(set(boards)) > 1


