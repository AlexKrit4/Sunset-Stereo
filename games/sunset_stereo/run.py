"""Generate Stake Engine books and configs for Sunset Stereo 6x4 ways."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from gamestate import GameState
from game_config import BUY_BONUS_BOOKS, GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from weight_bonus import weight_bonus_lookup


def _write_fallback_index(config) -> None:
    """Keep both ACP modes listed when base files are not in this checkout."""
    path = os.path.join(config.publish_path, "index.json")
    modes = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            modes = json.load(handle).get("modes", [])
    by_name = {mode["name"]: mode for mode in modes}
    by_name.setdefault(
        "base",
        {
            "name": "base",
            "cost": 1.0,
            "events": "books_base.jsonl.zst",
            "weights": "lookUpTable_base_0.csv",
        },
    )
    by_name["bonus"] = {
        "name": "bonus",
        "cost": 95.0,
        "events": "books_bonus.jsonl.zst",
        "weights": "lookUpTable_bonus_0.csv",
    }
    payload = {"modes": [by_name["base"], by_name["bonus"]]}
    from copy_publish import write_engine_index

    write_engine_index(path, payload["modes"])
    print("wrote fallback index.json")


if __name__ == "__main__":
    sim_mode = os.environ.get("SUNSET_SIM_MODE", "base").strip().lower()
    num_threads = 4
    rust_threads = 4
    profiling = False
    compression = True

    if sim_mode == "bonus":
        batching_size = 2500
        num_sim_args = {"bonus": int(BUY_BONUS_BOOKS)}
        run_conditions = {
            "run_sims": True,
            "run_optimization": False,
            "run_analysis": False,
            "run_format_checks": True,
        }
    else:
        batching_size = 5000
        num_sim_args = {"base": int(1_000_000)}
        run_conditions = {
            "run_sims": True,
            "run_optimization": True,
            "run_analysis": True,
            "run_format_checks": True,
        }

    target_modes = list(num_sim_args.keys())

    GameConfig._instance = None
    config = GameConfig()
    gamestate = GameState(config)
    OptimizationSetup(config)

    for mode in target_modes:
        lut_zero = os.path.join(config.publish_path, f"lookUpTable_{mode}_0.csv")
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

    try:
        generate_configs(gamestate)
    except FileNotFoundError as exc:
        print("generate_configs skipped missing files:", exc)
        _write_fallback_index(config)

    if sim_mode == "bonus":
        stats = weight_bonus_lookup(config.publish_path)
        print("weighted bonus LUT", stats)
        from copy_publish import verify_bonus_payouts

        verify_bonus_payouts(config.publish_path)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        create_stat_sheet(gamestate, custom_keys=[])

    if run_conditions["run_format_checks"]:
        excluded = ["base"] if sim_mode == "bonus" else []
        execute_all_tests(config, excluded_modes=excluded)
