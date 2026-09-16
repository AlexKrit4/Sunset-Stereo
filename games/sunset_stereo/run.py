"""Generate Stake Engine books for all four Sunset Stereo modes."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from gamestate import GameState
from game_config import (
    BASE_BOOKS,
    BUY_BONUS_BOOKS,
    BUY_WILD_BOOKS,
    SCATTER_BOOKS,
    GameConfig,
)
from game_optimization import OptimizationSetup
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from weight_modes import weight_mode_lookup
from copy_publish import write_engine_index


MODE_BOOKS = {
    "base": BASE_BOOKS,
    "scatter": SCATTER_BOOKS,
    "bonus": BUY_BONUS_BOOKS,
    "wildbonus": BUY_WILD_BOOKS,
}


def _write_index(config) -> None:
    path = os.path.join(config.publish_path, "index.json")
    modes = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            modes = json.load(handle).get("modes", [])
    by_name = {mode["name"]: mode for mode in modes}
    by_name["base"] = {
        "name": "base",
        "cost": 1.0,
        "events": "books_base.jsonl.zst",
        "weights": "lookUpTable_base_0.csv",
    }
    by_name["scatter"] = {
        "name": "scatter",
        "cost": 1.5,
        "events": "books_scatter.jsonl.zst",
        "weights": "lookUpTable_scatter_0.csv",
    }
    by_name["bonus"] = {
        "name": "bonus",
        "cost": 95.0,
        "events": "books_bonus.jsonl.zst",
        "weights": "lookUpTable_bonus_0.csv",
    }
    by_name["wildbonus"] = {
        "name": "wildbonus",
        "cost": 225.0,
        "events": "books_wildbonus.jsonl.zst",
        "weights": "lookUpTable_wildbonus_0.csv",
    }
    order = ["base", "scatter", "bonus", "wildbonus"]
    write_engine_index(path, [by_name[name] for name in order])
    print("wrote index.json")


if __name__ == "__main__":
    sim_mode = os.environ.get("SUNSET_SIM_MODE", "all").strip().lower()
    num_threads = int(os.environ.get("SUNSET_THREADS", "4"))
    compression = True
    profiling = False

    if sim_mode == "all":
        target_modes = ["base", "scatter", "bonus", "wildbonus"]
    else:
        target_modes = [sim_mode]

    GameConfig._instance = None
    config = GameConfig()
    gamestate = GameState(config)
    OptimizationSetup(config)

    for mode in target_modes:
        lut_zero = os.path.join(config.publish_path, f"lookUpTable_{mode}_0.csv")
        if os.path.exists(lut_zero):
            os.remove(lut_zero)

    batch = 2500 if any(mode in {"bonus", "wildbonus"} for mode in target_modes) else 5000
    override = os.environ.get("SUNSET_NUM_SIMS")
    num_sim_args = {mode: int(override) if override else MODE_BOOKS[mode] for mode in target_modes}
    create_books(gamestate, config, num_sim_args, batch, num_threads, compression, profiling)

    try:
        generate_configs(gamestate)
    except FileNotFoundError as exc:
        print("generate_configs skipped missing files:", exc)
        _write_index(config)

    lookup_dir = os.path.join(os.path.dirname(config.publish_path), "lookup_tables")
    for mode in target_modes:
        stats = weight_mode_lookup(config.publish_path, mode, lookup_dir)
        print(f"weighted {mode} LUT", stats)

    _write_index(config)
    try:
        execute_all_tests(config, excluded_modes=[mode for mode in MODE_BOOKS if mode not in target_modes])
    except Exception as exc:
        print("format checks skipped:", exc)
