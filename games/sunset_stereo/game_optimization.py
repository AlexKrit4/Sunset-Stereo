"""Optimization fences: ~95% RTP, high volatility, 15000x ceiling."""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    ConstructFenceBias,
    verify_optimization_input,
)


class OptimizationSetup:
    def __init__(self, game_config):
        self.game_config = game_config
        # Fences must sum to betmode RTP 0.950.
        # High vol: most of the RTP sits in the bonus; max-win is a rare tail.
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.010, av_win=15000, search_conditions=15000
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.560, hr=180, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=5.0, rtp=0.380).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.1, "win_range": (1, 2), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 1.3, "win_range": (8, 20), "probability": 1.0},
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.85,
                            "win_range": (20, 80),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 1.25,
                            "win_range": (200, 800),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=8000,
                    num_per_fence=12000,
                    min_m2m=8,
                    max_m2m=20,
                    pmb_rtp=1.0,
                    sim_trials=8000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"],
                    bias_ranges=[(2.0, 4.0)],
                    bias_weights=[0.4],
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
