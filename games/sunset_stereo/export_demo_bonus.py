"""Write a few buy-bonus books into the frontend mock pack."""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from game_config import GameConfig
from gamestate import GameState

DEMO = os.path.join(ROOT, "apps", "sunset-stereo", "src", "rgs", "demoBooks.json")


def one_book(criteria: str, sim: int) -> dict:
    GameConfig._instance = None
    state = GameState(GameConfig())
    state.betmode = "bonus"
    state.criteria = criteria
    state.run_spin(sim)
    book = state.book.to_json()
    book["id"] = 90_000 + sim
    return book


def main() -> None:
    with open(DEMO, encoding="utf-8") as handle:
        pack = json.load(handle)
    books = [
        one_book("dead", 11),
        one_book("dead", 17),
        one_book("recoup", 21),
        one_book("recoup", 29),
    ]
    pack["bonusBooks"] = books
    with open(DEMO, "w", encoding="utf-8") as handle:
        json.dump(pack, handle, separators=(",", ":"))
        handle.write("\n")
    for book in books:
        print(book["id"], book.get("criteria"), book["payoutMultiplier"], "events", len(book["events"]))


if __name__ == "__main__":
    main()
