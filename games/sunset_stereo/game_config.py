"""Sunset Stereo configuration — 6x4 ways (production)."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


# 3-scatter buy: debit is 95× the selected 1× bet. Book payouts stay in 1× units.
BUY_BONUS_COST = 95.0
BUY_BONUS_BOOKS = 50_000
BUY_BONUS_DEAD = 37_500
BUY_BONUS_RECOUP = 12_490
BUY_BONUS_WINCAP = 10

# Extra-play alphabet. Independent cell draws, not per-reel scripted strips.
BONUS_PAYING = ["H1", "H2", "H3", "H4", "H5", "L1", "L2", "L3", "L4", "L5"]

# Book-count mix for the 50k pack. Weights (RTP) are applied later.
# Dead 75% of books, recoup 25%. Bands are in 1× stake units.
DEAD_BANDS = (
    (0.0, 0.1, 220),
    (0.1, 20.0, 280),
    (20.0, 50.0, 280),
    (50.0, 95.0, 220),
)
RECOUP_BANDS = (
    (95.0, 200.0, 480),
    (200.0, 500.0, 200),
    (500.0, 1000.0, 140),
    (1000.0, 2000.0, 90),
    (2000.0, 5000.0, 55),
    (5000.0, 10000.0, 25),
    (10000.0, 15000.0, 10),
)


def bonus_payout_band(criteria: str, sim: int) -> tuple[float, float] | None:
    """Target payout window for one buy-bonus book, in 1× units."""
    if criteria == "wincap":
        return (15000.0, 15000.0)
    slot = (int(sim) * 1103515245 + 12345) % 1000
    table = DEAD_BANDS if criteria == "dead" else RECOUP_BANDS if criteria == "recoup" else None
    if table is None:
        return None
    acc = 0
    for lo, hi, weight in table:
        acc += weight
        if slot < acc:
            return (lo, hi)
    return (table[-1][0], table[-1][1])


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
        self.rtp = 0.9500
        self.output_regular_json = False
        self.construct_paths()

        self.num_reels = 6
        self.num_rows = [4] * self.num_reels
        self.paytable = WAYS_PAYTABLE
        self.paylines = {}

        self.include_padding = True
        # Scatter is visual/tease in base; 3+ suns start 10 extra plays.
        self.special_symbols = {"wild": [], "scatter": ["S"]}

        self.freespin_triggers = {
            self.basegame_type: {3: 10, 4: 10},
            self.freegame_type: {},
        }
        # Board anticipation after two suns (player 2-scatter tease).
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

        # Same strips for every bucket. Max-win books are natural bonus games
        # that crossed 15000x and were cut off — not a fake all-vinyl reel.
        freegame_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 90, 4: 10},
            "force_wincap": False,
            "force_freegame": True,
        }
        wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 90, 4: 10},
            "force_wincap": True,
            "force_freegame": True,
        }
        basegame_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        zerowin_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "force_wincap": False,
            "force_freegame": False,
        }

        bonus_dead_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 1},
            "force_wincap": False,
            "force_freegame": True,
        }
        bonus_recoup_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 1},
            "force_wincap": False,
            "force_freegame": True,
        }
        bonus_wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR_WCAP": 1},
            },
            "scatter_triggers": {3: 1},
            "force_wincap": True,
            "force_freegame": True,
        }

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
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions=wincap_condition,
                    ),
                    Distribution(criteria="freegame", quota=0.04, conditions=freegame_condition),
                    Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions=zerowin_condition),
                    Distribution(criteria="basegame", quota=0.559, conditions=basegame_condition),
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
                        fixed_amt=BUY_BONUS_WINCAP,
                        win_criteria=self.wincap,
                        conditions=bonus_wincap_condition,
                    ),
                    Distribution(
                        criteria="dead",
                        fixed_amt=BUY_BONUS_DEAD,
                        conditions=bonus_dead_condition,
                    ),
                    Distribution(
                        criteria="recoup",
                        fixed_amt=BUY_BONUS_RECOUP,
                        conditions=bonus_recoup_condition,
                    ),
                ],
            ),
        ]
