"""Checks for the Stake Engine math pack in publish/sunset_stereo/."""

import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLISH = os.path.join(ROOT, "publish", "sunset_stereo")


def test_publish_index_is_base_only():
    with open(os.path.join(PUBLISH, "index.json"), encoding="utf-8") as handle:
        index = json.load(handle)
    assert [mode["name"] for mode in index["modes"]] == ["base"]
    mode = index["modes"][0]
    assert mode["cost"] == 1.0
    assert mode["events"] == "books_base.jsonl.zst"
    assert mode["weights"] == "lookUpTable_base_0.csv"
    assert os.path.isfile(os.path.join(PUBLISH, mode["events"]))
    assert os.path.isfile(os.path.join(PUBLISH, mode["weights"]))


def test_lookup_table_payouts_are_tenths_and_capped():
    path = os.path.join(PUBLISH, "lookUpTable_base_0.csv")
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) in {1000, 1_000_000}
    ids = []
    max_cents = 0
    for book_id, weight, payout in rows:
        ids.append(int(book_id))
        assert int(weight) >= 1
        cents = int(payout)
        assert cents >= 0
        assert cents % 10 == 0
        if cents > max_cents:
            max_cents = cents
    assert ids[0] == 0
    assert ids == list(range(len(rows)))
    if len(rows) == 1_000_000:
        assert max_cents == 1_500_000
