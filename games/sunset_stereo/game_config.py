"""Sunset Stereo configuration — 6x4 ways, four Stake modes."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


BUY_BONUS_COST = 95.0
BUY_WILD_COST = 225.0
SCATTER_COST = 1.5
TARGET_RTP = 0.9500

BASE_BOOKS = 1_000_000
SCATTER_BOOKS = 1_000_000
BUY_BONUS_BOOKS = 250_000
BUY_WILD_BOOKS = 250_000

# 3-scatter every 200, 4-scatter every 1000 in the 1× base pack.
BASE_FG3 = 5_000
BASE_FG4 = 1_000
BASE_WINCAP = 20
BASE_HITS = 244_000 - BASE_WINCAP
BASE_ZEROS = BASE_BOOKS - BASE_HITS - BASE_FG3 - BASE_FG4 - BASE_WINCAP

# 3-scatter every 100, 4-scatter every 500 in the 1.5× ante pack.
SCATTER_FG3 = 10_000
SCATTER_FG4 = 2_000
SCATTER_WINCAP = 20
SCATTER_HITS = 338_000 - SCATTER_WINCAP
SCATTER_ZEROS = SCATTER_BOOKS - SCATTER_HITS - SCATTER_FG3 - SCATTER_FG4 - SCATTER_WINCAP

# 95× buy: ~18% recoup, min 3×. 225× buy: ~10% recoup, min 5×.
BONUS_WINCAP = 20
BONUS_RECOUP = 44_980
BONUS_DEAD = BUY_BONUS_BOOKS - BONUS_RECOUP - BONUS_WINCAP
WILD_WINCAP = 30
WILD_RECOUP = 24_970
WILD_DEAD = BUY_WILD_BOOKS - WILD_RECOUP - WILD_WINCAP

BONUS_PAYING = ["H1", "H2", "H3", "H4", "H5", "L1", "L2", "L3", "L4", "L5"]
SCATTER_REELS = (1, 2, 3, 4)
REEL2 = 1

# Natural bonus books (base / ante) must pay at least 10×.
NATURAL_BONUS_MIN = 10.0
BUY_BONUS_MIN = 3.0
BUY_WILD_MIN = 5.0


def _assert_counts() -> None:
    assert BASE_ZEROS + BASE_HITS + BASE_FG3 + BASE_FG4 + BASE_WINCAP == BASE_BOOKS
    assert SCATTER_ZEROS + SCATTER_HITS + SCATTER_FG3 + SCATTER_FG4 + SCATTER_WINCAP == SCATTER_BOOKS
    assert BONUS_DEAD + BONUS_RECOUP + BONUS_WINCAP == BUY_BONUS_BOOKS
    assert WILD_DEAD + WILD_RECOUP + WILD_WINCAP == BUY_WILD_BOOKS
    assert BASE_ZEROS == 750_000
    assert BASE_FG3 * 200 == BASE_BOOKS
    assert BASE_FG4 * 1000 == BASE_BOOKS
    assert SCATTER_FG3 * 100 == SCATTER_BOOKS
    assert SCATTER_FG4 * 500 == SCATTER_BOOKS


_assert_counts()

# Matches apps/sunset-stereo/src/math/config.js PAYOUTS (H1=high1 … L5=low5).
WAYS_PAYTABLE = {
    (6, "H1"): 20,
    (5, "H1"): 6,
    (4, "H1"): 3,
    (3, "H1"): 0.9,
    (6, "H2"): 10,
    (5, "H2"): 3.2,
    (4, "H2"): 0.6,
    (3, "H2"): 0.4,
    (6, "H3"): 4.8,
    (5, "H3"): 1.6,
    (4, "H3"): 0.5,
    (3, "H3"): 0.3,
    (6, "H4"): 4,
    (5, "H4"): 1.2,
    (4, "H4"): 0.5,
    (3, "H4"): 0.3,
    (6, "H5"): 3.2,
    (5, "H5"): 0.9,
    (4, "H5"): 0.4,
    (3, "H5"): 0.3,
    (6, "L1"): 2.8,
    (5, "L1"): 0.8,
    (4, "L1"): 0.4,
    (3, "L1"): 0.2,
    (6, "L2"): 2.8,
    (5, "L2"): 0.7,
    (4, "L2"): 0.4,
    (3, "L2"): 0.2,
    (6, "L3"): 2,
    (5, "L3"): 0.7,
    (4, "L3"): 0.3,
    (3, "L3"): 0.2,
    (6, "L4"): 2,
    (5, "L4"): 0.6,
    (4, "L4"): 0.3,
    (3, "L4"): 0.2,
    (6, "L5"): 1.4,
    (5, "L5"): 0.5,
    (4, "L5"): 0.2,
    (3, "L5"): 0.2,
}


def bonus_payout_band(mode: str, criteria: str, sim: int) -> tuple[float, float] | None:
    """Target payout window for one book, in 1× units."""
    if criteria == "wincap":
        return (15000.0, 15000.0)
    rng_slot = (int(sim) * 1103515245 + 12345) % 1000
    if mode in {"base", "scatter"} and criteria in {"freegame", "freegame4"}:
        table = (
            (10.0, 25.0, 220),
            (25.0, 60.0, 220),
            (60.0, 100.0, 180),
            (100.0, 200.0, 150),
            (200.0, 500.0, 120),
            (500.0, 1000.0, 60),
            (1000.0, 3000.0, 30),
            (3000.0, 8000.0, 15),
            (8000.0, 14999.9, 5),
        )
        if mode == "scatter":
            table = (
                (10.0, 30.0, 280),
                (30.0, 70.0, 260),
                (70.0, 100.0, 200),
                (100.0, 200.0, 140),
                (200.0, 500.0, 70),
                (500.0, 1500.0, 30),
                (1500.0, 5000.0, 15),
                (5000.0, 14999.9, 5),
            )
    elif mode == "bonus" and criteria == "dead":
        table = (
            (3.0, 8.0, 140),
            (8.0, 20.0, 180),
            (20.0, 40.0, 200),
            (40.0, 70.0, 220),
            (70.0, 95.0, 260),
        )
    elif mode == "bonus" and criteria == "recoup":
        table = (
            (95.0, 140.0, 280),
            (140.0, 250.0, 240),
            (250.0, 500.0, 200),
            (500.0, 1200.0, 140),
            (1200.0, 3000.0, 80),
            (3000.0, 8000.0, 40),
            (8000.0, 14999.9, 20),
        )
    elif mode == "wildbonus" and criteria == "dead":
        table = (
            (5.0, 15.0, 200),
            (15.0, 40.0, 240),
            (40.0, 90.0, 220),
            (90.0, 160.0, 180),
            (160.0, 225.0, 160),
        )
    elif mode == "wildbonus" and criteria == "recoup":
        table = (
            (225.0, 400.0, 220),
            (400.0, 800.0, 220),
            (800.0, 2000.0, 220),
            (2000.0, 5000.0, 180),
            (5000.0, 10000.0, 100),
            (10000.0, 14999.9, 60),
        )
    else:
        return None
    acc = 0
    for lo, hi, weight in table:
        acc += weight
        if rng_slot < acc:
            return (lo, hi)
    return (table[-1][0], table[-1][1])


class GameConfig(Config):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "sunset_stereo"
        self.provider_number = 77
        self.provider_name = "sunset_stereo"
        self.working_name = "Sunset Stereo"
        self.game_name = "Sunset Stereo"
        self.wincap = 15000.0
        self.win_type = "ways"
        self.rtp = TARGET_RTP
        self.output_regular_json = False
        self.construct_paths()

        self.num_reels = 6
        self.num_rows = [4] * self.num_reels
        self.paytable = WAYS_PAYTABLE
        self.paylines = {}

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"]}

        self.freespin_triggers = {
            self.basegame_type: {3: 10, 4: 10},
            self.freegame_type: {},
        }
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 2,
        }

        reels = {
            "BR0": "BR0.csv",
            "FR0": "FR0.csv",
            "FR_DEAD": "FR_DEAD.csv",
            "FR_RECOUP": "FR_RECOUP.csv",
            "FR_WCAP": "FR_WCAP.csv",
        }
        self.reels = {}
        for reel_id, filename in reels.items():
            self.reels[reel_id] = self.read_reels_csv(os.path.join(self.reels_path, filename))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]
        self.padding_symbol_values = {}

        base_reels = {
            self.basegame_type: {"BR0": 1},
            self.freegame_type: {"FR0": 1},
        }
        base_only = {self.basegame_type: {"BR0": 1}}

        def cond(force_fg=False, force_cap=False, scatters=None, reel2=False, wilds=False):
            payload = {
                "reel_weights": dict(base_reels if force_fg else base_only),
                "force_wincap": force_cap,
                "force_freegame": force_fg,
                "force_reel2_scatter": reel2,
                "place_bonus_wild": wilds,
            }
            if scatters is not None:
                payload["scatter_triggers"] = scatters
            return payload

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=BASE_WINCAP / BASE_BOOKS,
                        win_criteria=self.wincap,
                        conditions=cond(True, True, {4: 1}, wilds=True),
                    ),
                    Distribution(
                        criteria="freegame4",
                        quota=BASE_FG4 / BASE_BOOKS,
                        conditions=cond(True, False, {4: 1}, wilds=True),
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=BASE_FG3 / BASE_BOOKS,
                        conditions=cond(True, False, {3: 1}),
                    ),
                    Distribution(criteria="0", quota=BASE_ZEROS / BASE_BOOKS, win_criteria=0.0, conditions=cond()),
                    Distribution(criteria="basegame", quota=BASE_HITS / BASE_BOOKS, conditions=cond()),
                ],
            ),
            BetMode(
                name="scatter",
                cost=SCATTER_COST,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=SCATTER_WINCAP / SCATTER_BOOKS,
                        win_criteria=self.wincap,
                        conditions=cond(True, True, {4: 1}, reel2=True, wilds=True),
                    ),
                    Distribution(
                        criteria="freegame4",
                        quota=SCATTER_FG4 / SCATTER_BOOKS,
                        conditions=cond(True, False, {4: 1}, reel2=True, wilds=True),
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=SCATTER_FG3 / SCATTER_BOOKS,
                        conditions=cond(True, False, {3: 1}, reel2=True),
                    ),
                    Distribution(
                        criteria="0",
                        quota=SCATTER_ZEROS / SCATTER_BOOKS,
                        win_criteria=0.0,
                        conditions=cond(reel2=True),
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=SCATTER_HITS / SCATTER_BOOKS,
                        conditions=cond(reel2=True),
                    ),
                ],
            ),
            BetMode(
                name="bonus",
                cost=BUY_BONUS_COST,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        fixed_amt=BONUS_WINCAP,
                        win_criteria=self.wincap,
                        conditions=cond(True, True, {3: 1}),
                    ),
                    Distribution(criteria="dead", fixed_amt=BONUS_DEAD, conditions=cond(True, False, {3: 1})),
                    Distribution(criteria="recoup", fixed_amt=BONUS_RECOUP, conditions=cond(True, False, {3: 1})),
                ],
            ),
            BetMode(
                name="wildbonus",
                cost=BUY_WILD_COST,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        fixed_amt=WILD_WINCAP,
                        win_criteria=self.wincap,
                        conditions=cond(True, True, {4: 1}, wilds=True),
                    ),
                    Distribution(
                        criteria="dead",
                        fixed_amt=WILD_DEAD,
                        conditions=cond(True, False, {4: 1}, wilds=True),
                    ),
                    Distribution(
                        criteria="recoup",
                        fixed_amt=WILD_RECOUP,
                        conditions=cond(True, False, {4: 1}, wilds=True),
                    ),
                ],
            ),
        ]
