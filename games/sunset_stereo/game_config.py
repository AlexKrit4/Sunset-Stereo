"""Sunset Stereo configuration — 6x4 ways (production)."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


# Matches apps/sunset-stereo/src/math/config.js PAYOUTS (H1=high1 … L5=low5).
WAYS_PAYTABLE = {
    (6, "H1"): 20,
    (5, "H1"): 6,
    (4, "H1"): 3,
    (3, "H1"): 0.88,
    (6, "H2"): 10,
    (5, "H2"): 3.2,
    (4, "H2"): 0.6,
    (3, "H2"): 0.4,
    (6, "H3"): 4.8,
    (5, "H3"): 1.6,
    (4, "H3"): 0.52,
    (3, "H3"): 0.32,
    (6, "H4"): 4,
    (5, "H4"): 1.2,
    (4, "H4"): 0.48,
    (3, "H4"): 0.28,
    (6, "H5"): 3.2,
    (5, "H5"): 0.88,
    (4, "H5"): 0.4,
    (3, "H5"): 0.28,
    (6, "L1"): 2.8,
    (5, "L1"): 0.8,
    (4, "L1"): 0.36,
    (3, "L1"): 0.24,
    (6, "L2"): 2.8,
    (5, "L2"): 0.72,
    (4, "L2"): 0.36,
    (3, "L2"): 0.24,
    (6, "L3"): 2,
    (5, "L3"): 0.68,
    (4, "L3"): 0.32,
    (3, "L3"): 0.2,
    (6, "L4"): 2,
    (5, "L4"): 0.6,
    (4, "L4"): 0.28,
    (3, "L4"): 0.2,
    (6, "L5"): 1.4,
    (5, "L5"): 0.52,
    (4, "L5"): 0.24,
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
        self.wincap = 55200.0
        self.win_type = "ways"
        self.rtp = 0.9600
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

        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        for reel_id, filename in reels.items():
            self.reels[reel_id] = self.read_reels_csv(os.path.join(self.reels_path, filename))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]
        self.padding_symbol_values = {}

        freegame_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 90, 4: 10},
            "force_wincap": False,
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
        wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 80, 4: 20},
            "force_wincap": True,
            "force_freegame": True,
        }
        # Restore wincap_condition before Stake optimization / ACP upload.
        _ = wincap_condition

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
                    Distribution(criteria="freegame", quota=0.1, conditions=freegame_condition),
                    Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions=zerowin_condition),
                    Distribution(criteria="basegame", quota=0.5, conditions=basegame_condition),
                ],
            ),
        ]
