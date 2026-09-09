"""Checks for the Stake Engine math pack in publish/sunset_stereo/."""

import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLISH = os.path.join(ROOT, "publish", "sunset_stereo")


def test_publish_index_lists_base_and_optional_bonus():
    with open(os.path.join(PUBLISH, "index.json"), encoding="utf-8") as handle:
        index = json.load(handle)
    modes = {mode["name"]: mode for mode in index["modes"]}
    assert "base" in modes
    assert modes["base"]["cost"] == 1.0
    assert modes["base"]["events"] == "books_base.jsonl.zst"
    assert modes["base"]["weights"] == "lookUpTable_base_0.csv"
    if "bonus" in modes:
        assert [mode["name"] for mode in index["modes"]][:2] == ["base", "bonus"]
        assert modes["bonus"]["cost"] == 95.0
        assert modes["bonus"]["events"] == "books_bonus.jsonl.zst"
        assert modes["bonus"]["weights"] == "lookUpTable_bonus_0.csv"


def _assert_lookup(path: str, expect_cap: bool) -> None:
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows
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
    assert ids == sorted(ids)
    if expect_cap and len(rows) >= 1000:
        assert max_cents == 1_500_000


def test_lookup_table_payouts_are_tenths_and_capped():
    base = os.path.join(PUBLISH, "lookUpTable_base_0.csv")
    bonus = os.path.join(PUBLISH, "lookUpTable_bonus_0.csv")
    if os.path.isfile(base):
        with open(base, newline="", encoding="utf-8") as handle:
            n = sum(1 for _ in handle)
        _assert_lookup(base, expect_cap=(n in {1000, 1_000_000}))
    if os.path.isfile(bonus):
        _assert_lookup(bonus, expect_cap=True)
        with open(bonus, newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        total_w = sum(int(row[1]) for row in rows)
        dead_w = sum(int(row[1]) for row in rows if int(row[2]) < 9500)
        recoup_w = total_w - dead_w
        expected = sum(int(row[1]) * (int(row[2]) / 100.0) for row in rows) / total_w
        assert abs(dead_w / total_w - 0.75) < 0.01
        assert abs(recoup_w / total_w - 0.25) < 0.01
        assert 0.94 <= expected / 95.0 <= 0.96
