"""LUT weighting replaced the Rust optimizer so every unique book stays in the pack."""


class OptimizationSetup:
    def __init__(self, game_config):
        self.game_config = game_config
        self.game_config.opt_params = {}
