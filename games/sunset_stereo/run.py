"""Generate Stake Engine books and configs for Sunset Stereo 6x4 ways."""

import os

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":
    num_threads = 1
    rust_threads = 1
    batching_size = 1000
    compression = True
    profiling = False

    # 1000 books is a Stake Engine *test* pack, not the production volume.
    num_sim_args = {
        "base": int(1000),
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "run_format_checks": True,
    }
    target_modes = list(num_sim_args.keys())

    config = GameConfig()
    gamestate = GameState(config)
    OptimizationSetup(config)

    lut_zero = os.path.join(config.publish_path, "lookUpTable_base_0.csv")
    if os.path.exists(lut_zero):
        os.remove(lut_zero)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        create_stat_sheet(gamestate, custom_keys=[])

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)
