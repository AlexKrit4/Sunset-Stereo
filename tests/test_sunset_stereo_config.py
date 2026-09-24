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


def test_left_wild_starts_ways_for_other_symbols():
    from gamestate import GameState

    GameConfig._instance = None
    state = GameState(GameConfig())
    names = [
        ["W", "H5", "H4", "H3"],
        ["L1", "H2", "H5", "H4"],
        ["L1", "H2", "H5", "H3"],
        ["L4", "L5", "L2", "L3"],
        ["L4", "L5", "L2", "L3"],
        ["L4", "L5", "L2", "L3"],
    ]
    state.board = [[state.create_symbol(name) for name in col] for col in names]
    state.evaluate_ways_board(emit_events=False)
    assert float(state.win_data["totalWin"]) > 0
    assert "L1" in {win["symbol"] for win in state.win_data["wins"]}


def test_screenshot_left_wild_speaker_line_pays():
    """W on reel 0 + speakers on reels 1–2 is a 3-oak L1, same as the frontend."""
    from gamestate import GameState

    GameConfig._instance = None
    state = GameState(GameConfig())
    names = [
        ["W", "L3", "L5", "H4"],
        ["L1", "H2", "L4", "L3"],
        ["L1", "H1", "H3", "L5"],
        ["H4", "L1", "H3", "H1"],
        ["L1", "L3", "H2", "L4"],
        ["H1", "H2", "H3", "L2"],
    ]
    state.board = [[state.create_symbol(name) for name in col] for col in names]
    state.evaluate_ways_board(emit_events=False)
    assert float(state.win_data["totalWin"]) > 0
    assert "L1" in {win["symbol"] for win in state.win_data["wins"]}


def _extra_play_chunks(types: list[str]) -> list[list[str]]:
    starts = [index for index, kind in enumerate(types) if kind == "updateFreeSpin"]
    chunks = []
    for offset, start in enumerate(starts):
        end = starts[offset + 1] if offset + 1 < len(starts) else len(types)
        chunks.append(types[start:end])
    return chunks


def test_bonus_paying_extra_plays_hold_and_respin():
    modes = (
        ("bonus", "dead"),
        ("wildbonus", "dead"),
        ("bonus", "recoup"),
        ("wildbonus", "recoup"),
        ("wildbonus", "wincap"),
        ("bonus", "wincap"),
    )
    for mode, criteria in modes:
        paid = 0
        for sim in range(12):
            _state, book = _mode_book(mode, criteria, sim)
            types = [event["type"] for event in book["events"]]
            for chunk in _extra_play_chunks(types):
                if "winInfo" not in chunk:
                    continue
                assert "holdRespin" in chunk, (mode, criteria, sim, chunk)
                assert chunk.count("reveal") >= 2, (mode, criteria, sim, chunk)
                hold_at = max(index for index, kind in enumerate(chunk) if kind == "holdRespin")
                win_at = chunk.index("winInfo")
                assert "reveal" in chunk[hold_at + 1 : win_at], (mode, criteria, sim, chunk)
                paid += 1
        assert paid >= 1, (mode, criteria)


def test_growing_hold_stages_are_two_or_three_respins():
    from ways_paint import growing_hold_stages, opening_respin_count

    occupied = {
        (0, 0): "H1",
        (0, 1): "H1",
        (1, 0): "H1",
        (1, 1): "H1",
        (2, 0): "H1",
        (3, 0): "H1",
        (4, 0): "H1",
        (5, 2): "W",
    }
    for seed in (2, 3):
        n_respins = opening_respin_count(seed)
        stages = growing_hold_stages(occupied, n_respins=n_respins)
        assert len(stages) == n_respins + 1
        assert stages[-1] == occupied
        assert (5, 2) in stages[0]
        assert len(stages[0]) <= len(stages[-1])


def test_bonus_opening_swaps_first_pay_and_stages_it():
    from ways_paint import delay_opening_win

    delayed = 0
    staged = 0
    for mode, criteria in (
        ("bonus", "dead"),
        ("wildbonus", "dead"),
        ("bonus", "recoup"),
        ("wildbonus", "recoup"),
        ("base", "freegame"),
        ("base", "freegame4"),
    ):
        for sim in range(16):
            _state, book = _mode_book(mode, criteria, sim)
            payout = book["payoutMultiplier"]
            types = [event["type"] for event in book["events"]]
            chunks = _extra_play_chunks(types)
            if not chunks:
                continue
            assert types.count("updateFreeSpin") == 10 or "wincap" in types
            has_dead = any("winInfo" not in chunk for chunk in chunks)
            first_pays = "winInfo" in chunks[0]
            if has_dead and delay_opening_win(sim) and "wincap" not in chunks[0]:
                delayed += 1
                assert not first_pays, (mode, criteria, sim, chunks[0])
            if first_pays:
                holds = chunks[0].count("holdRespin")
                assert holds in (2, 3), (mode, criteria, sim, chunks[0])
                assert chunks[0].count("reveal") >= holds + 1
            paying = [chunk for chunk in chunks if "winInfo" in chunk]
            if not paying:
                continue
            assert any(chunk.count("holdRespin") in (2, 3) for chunk in paying), (mode, criteria, sim)
            staged += 1
            final = next(event for event in book["events"] if event["type"] == "finalWin")
            assert int(final["amount"]) == int(payout)
    assert delayed >= 8
    assert staged >= 8


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
    from base_feature import should_feature
    from ways_paint import is_stacked_column_board, visible_ways_win

    boards = []
    sims = [sim for sim in range(20) if not should_feature(sim)][:12]
    for sim in sims:
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
    from base_feature import should_feature

    payouts = []
    boards = []
    sims = [sim for sim in range(120) if not should_feature(sim)][:80]
    for sim in sims:
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


def _synth_bonus_freq_rows(mode: str, with_feature: bool = False):
    """Small pack that mirrors Stake 1/N bonus quotas plus empty-book RTP padding."""
    from bonus_freq import BONUS_FREQ, FEATURE_RATE

    freq = BONUS_FREQ[mode]
    n = 20_000
    n3 = int(round(n * freq["fg3"]))
    n4 = int(round(n * freq["fg4"]))
    n_feat = int(round(n * FEATURE_RATE)) if with_feature else 0
    n_zero = int(round(n * (0.70 if mode == "base" else 0.60)))
    n_hit = n - n3 - n4 - n_zero - n_feat
    rows = []
    classes = {}
    book_id = 1

    def add(kind: str, cents: int, count: int) -> None:
        nonlocal book_id
        for _ in range(count):
            rows.append((book_id, 1, cents))
            classes[book_id] = kind
            book_id += 1

    add("fg3", 1000, max(1, n3 - 8))  # 10×
    add("fg3", 2500, 4)
    add("fg3", 12000, 2)
    add("fg3", 90000, 1)
    add("fg3", 1_500_000, 1)
    add("fg4", 1000, max(1, n4 - 6))
    add("fg4", 4000, 3)
    add("fg4", 25000, 1)
    add("fg4", 180000, 1)
    add("fg4", 1_500_000, 1)
    if n_feat:
        n_sync = n_feat // 2
        n_wild = n_feat - n_sync
        add("feature_sync", 0, n_sync // 2)
        add("feature_sync", 40, n_sync - n_sync // 2)
        add("feature_w1", 0, max(1, int(round(n_wild * 0.80))))
        add("feature_w2", 40, max(1, int(round(n_wild * 0.15))))
        add("feature_w3", 80, max(1, int(round(n_wild * 0.04))))
        add("feature_w4", 120, max(1, n_wild - sum(1 for kind in classes.values() if kind.startswith("feature_w"))))
    for cents in (20, 40, 80, 150, 300, 600, 1200, 3500) * ((n_hit // 8) + 1):
        if sum(1 for _, kind in classes.items() if kind == "hit") >= n_hit:
            break
        add("hit", cents, 1)
    add("zero", 0, n_zero)
    return rows, classes


def test_bonus_freq_weights_lock_one_in_rates_and_rtp():
    from bonus_freq import BONUS_FREQ, reweight_mode_rows

    for mode in ("base", "scatter"):
        rows, classes = _synth_bonus_freq_rows(mode)
        weighted, stats = reweight_mode_rows(rows, mode, classes)
        freq = stats["bonus_freq"]["classes"]
        want = BONUS_FREQ[mode]
        assert abs(freq["fg3"]["p"] - want["fg3"]) / want["fg3"] < 0.08
        assert abs(freq["fg4"]["p"] - want["fg4"]) / want["fg4"] < 0.08
        assert 0.93 <= stats["rtp"] <= 0.97
        assert stats["hit_rate"] >= 1 / 50
        assert freq["zero"]["p"] > 0.4
        cheap_fg3 = [weight for book_id, weight, cents in weighted if classes[book_id] == "fg3" and cents <= 1500]
        rich_fg3 = [weight for book_id, weight, cents in weighted if classes[book_id] == "fg3" and cents >= 90000]
        assert min(cheap_fg3) > max(rich_fg3)


def test_classify_book_uses_criteria_and_scatter_count():
    from bonus_freq import classify_book, classify_events

    assert classify_book({"id": 1, "criteria": "freegame", "payoutMultiplier": 1200, "events": []}) == "fg3"
    assert classify_book({"id": 2, "criteria": "freegame4", "payoutMultiplier": 8000, "events": []}) == "fg4"
    assert classify_book({"id": 3, "criteria": "wincap", "payoutMultiplier": 1_500_000, "events": []}) == "fg4"
    assert classify_book({"id": 4, "criteria": "0", "payoutMultiplier": 0, "events": []}) == "zero"
    assert classify_book({"id": 5, "criteria": "basegame", "payoutMultiplier": 80, "events": []}) == "hit"
    assert (
        classify_book(
            {
                "id": 25,
                "criteria": "0",
                "payoutMultiplier": 0,
                "events": [{"type": "baseFeature", "kind": "syncReels", "reels": [0, 5]}],
            }
        )
        == "feature_sync"
    )
    three = [{"type": "freeSpinTrigger", "positions": [{}, {}, {}]}]
    four = [{"type": "freeSpinTrigger", "positions": [{}, {}, {}, {}]}, {"type": "placeWild"}]
    assert classify_events(three, 1000) == "fg3"
    assert classify_events(four, 8000) == "fg4"


def test_base_feature_mix_is_four_percent_then_fifty_fifty():
    from base_feature import FEATURE_RATE, assert_feature_mix, feature_spec, should_feature

    ids = list(range(25_000))
    counts = assert_feature_mix(ids)
    assert counts["feature"] == int(len(ids) * FEATURE_RATE)
    assert counts["sync"] == counts["wilds"] == counts["feature"] // 2
    assert counts["w1"] == 400
    assert counts["w2"] == 75
    assert counts["w3"] == 20
    assert counts["w4"] == 5
    assert should_feature(0) and should_feature(25) and not should_feature(1)
    assert feature_spec(0)["kind"] == "syncReels"
    assert feature_spec(0)["reels"] == [0, 5]
    assert feature_spec(25)["kind"] == "placeWilds"
    assert len(feature_spec(25)["positions"]) == 1


def test_ways_detail_counts_reel_zero_wild_with_following_symbols():
    from base_feature import ways_detail

    pay, wins = ways_detail(
        [
            ["W", "L3", "L5", "H4"],
            ["H1", "L2", "L4", "L3"],
            ["H1", "L4", "H3", "L5"],
            ["H4", "L1", "H3", "L2"],
            ["L1", "L3", "H2", "L4"],
            ["H2", "H3", "L2", "L5"],
        ]
    )
    assert pay > 0
    assert "H1" in {win["symbol"] for win in wins}
    h1 = next(win for win in wins if win["symbol"] == "H1")
    assert h1["kind"] == 3


def test_apply_feature_to_book_writes_event_and_may_stay_zero():
    from base_feature import apply_feature_to_book, feature_spec

    spec = feature_spec(50)
    assert spec["kind"] == "syncReels"
    book = {
        "id": 50,
        "payoutMultiplier": 0,
        "events": [
            {
                "index": 0,
                "type": "reveal",
                "gameType": "basegame",
                "board": [
                    [{"name": "L4"}] * 6,
                    [{"name": "L3"}] * 6,
                    [{"name": "L2"}] * 6,
                    [{"name": "L5"}] * 6,
                    [{"name": "H5"}] * 6,
                    [{"name": "H4"}] * 6,
                ],
            },
            {"index": 1, "type": "setTotalWin", "amount": 0},
            {"index": 2, "type": "finalWin", "amount": 0},
        ],
    }
    assert apply_feature_to_book(book) is True
    types = [event["type"] for event in book["events"]]
    assert types[0] == "baseFeature"
    assert book["events"][0]["kind"] == "syncReels"
    left, right = book["events"][0]["reels"]
    reveal = next(event for event in book["events"] if event["type"] == "reveal")
    assert reveal["board"][left] == reveal["board"][right]
    assert book["events"][-1]["type"] == "finalWin"
    assert int(book["events"][-1]["amount"]) == int(book["payoutMultiplier"])


def test_patch_wild_ways_locks_camera_wild_with_following_symbols():
    from patch_wild_ways_books import patch_book

    book = {
        "id": 9,
        "payoutMultiplier": 0,
        "events": [
            {"index": 0, "type": "reveal", "gameType": "basegame", "board": [[{"name": "S"}] * 6] * 6},
            {"index": 1, "type": "freeSpinTrigger", "totalFs": 10, "positions": []},
            {"index": 2, "type": "placeWild", "reel": 0, "row": 1},
            {"index": 3, "type": "updateFreeSpin", "amount": 0, "total": 10},
            {
                "index": 4,
                "type": "reveal",
                "gameType": "freegame",
                "board": [
                    [{"name": "L5"}, {"name": "L3"}, {"name": "L4"}, {"name": "H4"}, {"name": "L2"}, {"name": "L5"}],
                    [{"name": "L2"}, {"name": "H1"}, {"name": "L4"}, {"name": "L3"}, {"name": "L5"}, {"name": "L2"}],
                    [{"name": "L4"}, {"name": "H1"}, {"name": "H3"}, {"name": "L5"}, {"name": "L2"}, {"name": "L3"}],
                    [{"name": "H4"}, {"name": "L1"}, {"name": "H3"}, {"name": "L2"}, {"name": "L5"}, {"name": "H2"}],
                    [{"name": "L1"}, {"name": "L3"}, {"name": "H2"}, {"name": "L4"}, {"name": "L5"}, {"name": "H3"}],
                    [{"name": "H2"}, {"name": "H3"}, {"name": "L2"}, {"name": "L5"}, {"name": "L4"}, {"name": "H1"}],
                ],
            },
            {"index": 5, "type": "setTotalWin", "amount": 0},
            {"index": 6, "type": "finalWin", "amount": 0},
        ],
    }
    assert patch_book(book) is True
    types = [event["type"] for event in book["events"]]
    assert "winInfo" in types
    assert "holdRespin" in types
    reveal = next(event for event in book["events"] if event["type"] == "reveal" and event.get("gameType") == "freegame")
    wild_cell = reveal["board"][0][1]
    assert (wild_cell["name"] if isinstance(wild_cell, dict) else wild_cell) == "W"
    assert book["payoutMultiplier"] > 0
    assert book["events"][-1]["amount"] == book["payoutMultiplier"]


def test_bonus_freq_weights_lock_feature_rate_and_rtp():
    from bonus_freq import FEATURE_RATE, reweight_mode_rows

    for mode in ("base", "scatter"):
        rows, classes = _synth_bonus_freq_rows(mode, with_feature=True)
        weighted, stats = reweight_mode_rows(rows, mode, classes)
        freq = stats["bonus_freq"]["classes"]
        p_feat = sum(freq.get(kind, {}).get("p", 0.0) for kind in ("feature_sync", "feature_w1", "feature_w2", "feature_w3", "feature_w4"))
        assert abs(p_feat - FEATURE_RATE) / FEATURE_RATE < 0.08
        assert abs(freq["feature_sync"]["p"] - 0.5 * FEATURE_RATE) / (0.5 * FEATURE_RATE) < 0.12
        assert 0.93 <= stats["rtp"] <= 0.97


def test_generated_base_and_ante_feature_books_emit_event():
    from gamestate import GameState

    for mode, sim in (("base", 50), ("scatter", 0)):
        GameConfig._instance = None
        state = GameState(GameConfig())
        state.betmode = mode
        state.criteria = "basegame"
        state.run_spin(sim)
        book = state.book.to_json()
        assert book["events"][0]["type"] == "baseFeature"
        assert book["events"][0]["kind"] in {"syncReels", "placeWilds"}
        reveal = next(event for event in book["events"] if event["type"] == "reveal")
        assert reveal["gameType"] == "basegame"
        assert not any(event["type"] == "freeSpinTrigger" for event in book["events"])
        if book["events"][0]["kind"] == "syncReels":
            left, right = book["events"][0]["reels"]
            assert reveal["board"][left] == reveal["board"][right]


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


