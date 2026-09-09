"""Copy ACP math files listed in index.json into publish/sunset_stereo/.

Keeps already-published modes when a later run only regenerated one mode
(for example bonus-only after the 1M base pack).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import pickle
import shutil
from io import TextIOWrapper

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "games", "sunset_stereo", "library", "publish_files")
DST = os.path.join(ROOT, "publish", "sunset_stereo")
MODE_ORDER = ("base", "bonus")
INDEX_KEYS = ("name", "cost", "events", "weights")


def engine_index(modes: list) -> dict:
    """Stake Engine index.json: only name, cost, events, weights."""
    cleaned = []
    for mode in modes:
        cleaned.append(
            {
                "name": str(mode["name"]),
                "cost": float(mode["cost"]),
                "events": str(mode["events"]),
                "weights": str(mode["weights"]),
            }
        )
    return {"modes": cleaned}


def write_engine_index(path: str, modes: list) -> None:
    payload = engine_index(modes)
    text = json.dumps(payload, indent=4, ensure_ascii=True)
    leftover = text[json.JSONDecoder().raw_decode(text)[1] :]
    if leftover:
        raise ValueError(f"index.json has trailing data: {leftover!r}")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def verify_bonus_payouts(publish_dir: str) -> None:
    """Engine hashes book payoutMultiplier against LUT column 3, in file order."""
    books = os.path.join(publish_dir, "books_bonus.jsonl.zst")
    lut = os.path.join(publish_dir, "lookUpTable_bonus_0.csv")
    if not (os.path.isfile(books) and os.path.isfile(lut)):
        raise FileNotFoundError("bonus books or LUT missing")
    raw = open(lut, "rb").read()
    if b"\r" in raw:
        raise ValueError("lookUpTable_bonus_0.csv must use Unix \\n, not CRLF")
    lut_payouts = []
    lut_ids = []
    for book_id, _weight, payout in csv.reader(raw.decode("utf-8").splitlines()):
        lut_ids.append(int(book_id))
        lut_payouts.append(int(payout))
    import zstandard as zst

    book_payouts = []
    book_ids = []
    with open(books, "rb") as handle:
        with zst.ZstdDecompressor().stream_reader(handle) as reader:
            for line in TextIOWrapper(reader, encoding="utf-8"):
                if not line.strip():
                    continue
                blob = json.loads(line)
                book_ids.append(int(blob["id"]))
                book_payouts.append(int(blob["payoutMultiplier"]))
                final = next(event for event in blob["events"] if event["type"] == "finalWin")
                if int(final["amount"]) != int(blob["payoutMultiplier"]):
                    raise ValueError(
                        f"book {blob['id']} finalWin {final['amount']} != payoutMultiplier {blob['payoutMultiplier']}"
                    )
    if book_ids != lut_ids or book_payouts != lut_payouts:
        raise ValueError(
            f"bonus books/LUT payout mismatch: ids {book_ids[:3]} vs {lut_ids[:3]}, "
            f"len {len(book_payouts)} vs {len(lut_payouts)}"
        )
    if hashlib.md5(pickle.dumps(book_payouts)).hexdigest() != hashlib.md5(pickle.dumps(lut_payouts)).hexdigest():
        raise ValueError("bonus payout hash mismatch")
    print("bonus books/LUT payouts match", len(book_payouts), "rows")


def _load_index(path: str) -> dict:
    if not os.path.isfile(path):
        return {"modes": []}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    src_index = _load_index(os.path.join(SRC, "index.json"))
    os.makedirs(DST, exist_ok=True)
    merged = {mode["name"]: mode for mode in _load_index(os.path.join(DST, "index.json")).get("modes", [])}

    for mode in src_index.get("modes", []):
        events_src = os.path.join(SRC, mode["events"])
        weights_src = os.path.join(SRC, mode["weights"])
        if os.path.isfile(events_src) and os.path.isfile(weights_src):
            shutil.copy2(events_src, os.path.join(DST, mode["events"]))
            shutil.copy2(weights_src, os.path.join(DST, mode["weights"]))
            merged[mode["name"]] = mode
            print(f"copied {mode['name']}")
            if mode["name"] == "bonus":
                verify_bonus_payouts(DST)
        elif mode["name"] in merged:
            print(f"kept existing {mode['name']} (source files missing)")
        else:
            print(f"skip {mode['name']} (not generated yet)")

    modes = []
    seen = set()
    for name in MODE_ORDER:
        if name in merged:
            modes.append(merged[name])
            seen.add(name)
    for name, mode in merged.items():
        if name not in seen:
            modes.append(mode)

    write_engine_index(os.path.join(DST, "index.json"), modes)
    shutil.copy2(os.path.join(DST, "index.json"), os.path.join(SRC, "index.json"))
    print("wrote index.json")

    keep = {"index.json"}
    for mode in modes:
        keep.add(mode["events"])
        keep.add(mode["weights"])
    for name in os.listdir(DST):
        if name not in keep:
            os.remove(os.path.join(DST, name))
            print(f"removed leftover {name}")


if __name__ == "__main__":
    main()
