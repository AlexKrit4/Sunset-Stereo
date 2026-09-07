"""Sunset Stereo configuration — 5x3 lines game for Stake Engine."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


STANDARD_PAYLINES = {
    1: [0, 0, 0, 0, 0],
    2: [1, 1, 1, 1, 1],
    3: [2, 2, 2, 2, 2],
    4: [0, 1, 2, 1, 0],
    5: [2, 1, 0, 1, 2],
    6: [0, 0, 1, 2, 2],
    7: [2, 2, 1, 0, 0],
    8: [1, 0, 1, 2, 1],
    9: [1, 2, 1, 0, 1],
    10: [0, 1, 1, 1, 2],
    11: [2, 1, 1, 1, 0],
    12: [0, 1, 0, 1, 2],
    13: [2, 1, 2, 1, 0],
    14: [1, 1, 0, 1, 1],
    15: [1, 1, 2, 1, 1],
    16: [0, 2, 1, 0, 2],
    17: [2, 0, 1, 2, 0],
    18: [0, 0, 2, 0, 0],
    19: [2, 2, 0, 2, 2],
    20: [1, 0, 0, 0, 1],
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
        self.wincap = 5000.0
        self.win_type = "lines"
        self.rtp = 0.9600
        self.construct_paths()

        self.num_reels = 5
        self.num_rows = [3] * self.num_reels
        self.paytable = {
            (5, "W"): 80,
            (4, "W"): 25,
            (3, "W"): 12,
            (5, "H1"): 80,
            (4, "H1"): 25,
            (3, "H1"): 12,
            (5, "H2"): 25,
            (4, "H2"): 8,
            (3, "H2"): 4,
            (5, "H3"): 15,
            (4, "H3"): 5,
            (3, "H3"): 2.5,
            (5, "H4"): 10,
            (4, "H4"): 3,
            (3, "H4"): 1.5,
            (5, "L1"): 6,
            (4, "L1"): 1.5,
            (3, "L1"): 0.6,
            (5, "L2"): 4,
            (4, "L2"): 1,
            (3, "L2"): 0.4,
            (5, "L3"): 3,
            (4, "L3"): 0.8,
            (3, "L3"): 0.3,
            (5, "L4"): 2,
            (4, "L4"): 0.5,
            (3, "L4"): 0.2,
            (5, "L5"): 1.5,
            (4, "L5"): 0.4,
            (3, "L5"): 0.15,
        }
        self.paylines = STANDARD_PAYLINES

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": ["W"]}

        # Golden Hour: 3/4/5 suns award 10/14/18 encore spins.
        # Retrigger needs 3+ suns — no 2-scatter retrigger.
        self.freespin_triggers = {
            self.basegame_type: {3: 10, 4: 14, 5: 18},
            self.freegame_type: {3: 4, 4: 6, 5: 10},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "WCAP": "FRWCAP.csv"}
        self.reels = {}
        for reel_id, filename in reels.items():
            self.reels[reel_id] = self.read_reels_csv(os.path.join(self.reels_path, filename))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]
        self.padding_symbol_values = {
            "W": {"multiplier": {2: 90, 3: 55, 4: 40, 5: 35, 8: 20, 10: 12, 20: 6, 50: 2}}
        }

        freegame_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 55, 4: 18, 5: 4},
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: {2: 70, 3: 75, 4: 40, 5: 18, 8: 12, 10: 8, 20: 5, 50: 2},
            },
            "force_wincap": False,
            "force_freegame": True,
        }
        basegame_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "mult_values": {self.basegame_type: {1: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }
        wincap_condition = {
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1, "WCAP": 5},
            },
            "mult_values": {
                self.basegame_type: {1: 1},
                self.freegame_type: {2: 8, 3: 16, 4: 40, 5: 55, 8: 70, 10: 90, 20: 80, 50: 40},
            },
            "scatter_triggers": {4: 1, 5: 2},
            "force_wincap": True,
            "force_freegame": True,
        }
        zerowin_condition = {
            "reel_weights": {self.basegame_type: {"BR0": 1}},
            "mult_values": {self.basegame_type: {1: 1}},
            "force_wincap": False,
            "force_freegame": False,
        }

        mode_maxwins = {"base": 5000, "bonus": 5000}
        # wincap_condition stays available for production optimization runs.
        # The forced 5000x bucket is omitted from the default modes so a
        # small local sim finishes; add it back before ACP publication.
        _ = wincap_condition
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=mode_maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(criteria="freegame", quota=0.1, conditions=freegame_condition),
                    Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions=zerowin_condition),
                    Distribution(criteria="basegame", quota=0.5, conditions=basegame_condition),
                ],
            ),
            BetMode(
                name="bonus",
                cost=80.0,
                rtp=self.rtp,
                max_win=mode_maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="freegame", quota=1.0, conditions=freegame_condition),
                ],
            ),
        ]
