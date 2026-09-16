"""Write buy-bonus books into the frontend mock pack."""

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


def one_book(mode: str, criteria: str, sim: int, book_id: int) -> dict:
    GameConfig._instance = None
    state = GameState(GameConfig())
    state.betmode = mode
    state.criteria = criteria
    state.run_spin(sim)
    book = state.book.to_json()
    book["id"] = book_id
    book["criteria"] = criteria
    return book


def main() -> None:
    with open(DEMO, encoding="utf-8") as handle:
        pack = json.load(handle)
    pack["bonusBooks"] = [
        one_book("bonus", "dead", 11, 90011),
        one_book("bonus", "dead", 17, 90017),
        one_book("bonus", "recoup", 21, 90021),
        one_book("bonus", "recoup", 29, 90029),
    ]
    pack["wildBonusBooks"] = [
        one_book("wildbonus", "dead", 15, 92015),
        one_book("wildbonus", "dead", 19, 92019),
        one_book("wildbonus", "recoup", 21, 92021),
        one_book("wildbonus", "recoup", 27, 92027),
        one_book("wildbonus", "wincap", 3, 92003),
    ]
    with open(DEMO, "w", encoding="utf-8") as handle:
        json.dump(pack, handle, separators=(",", ":"))
        handle.write("\n")
    for key in ("bonusBooks", "wildBonusBooks"):
        for book in pack[key]:
            types = [event["type"] for event in book["events"]]
            print(
                key,
                book["id"],
                book.get("criteria"),
                book["payoutMultiplier"],
                "holdRespin",
                types.count("holdRespin"),
                "events",
                len(book["events"]),
            )


if __name__ == "__main__":
    main()
