"""Stamp the 4% base-spin feature and repair 4-scatter wild ways on published books.

Stake books own the outcome. This does not regenerate the 1M pack: it rewrites
existing base/ante jsonl.zst, updates LUT payouts, then reweights so feature
books stay at 4% and RTP stays ~95%.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from base_feature import apply_feature_to_book  # noqa: E402
from bonus_freq import reweight_publish_dir  # noqa: E402
from patch_wild_ways_books import patch_book  # noqa: E402

MODES = ("base", "scatter")


def _zstd_lines(path: str):
    proc = subprocess.Popen(
        ["zstd", "-d", "-c", "-T0", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout
    for line in proc.stdout:
        yield line
    err = proc.wait()
    if err:
        message = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", "replace")
        raise RuntimeError(f"zstd -d failed ({err}): {message[:400]}")


def patch_books_file_stream(path: str) -> tuple[dict[str, int], dict[int, int]]:
    stats = {"n": 0, "feature": 0, "wild_fix": 0}
    payouts: dict[int, int] = {}
    tmp = path + ".tmp"
    proc = subprocess.Popen(
        ["zstd", "-3", "-T0", "-f", "-o", tmp],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin
    for raw in _zstd_lines(path):
        line = raw.strip()
        if not line:
            continue
        book = json.loads(line)
        stats["n"] += 1
        if apply_feature_to_book(book):
            stats["feature"] += 1
        if patch_book(book):
            stats["wild_fix"] += 1
        payouts[int(book["id"])] = int(book.get("payoutMultiplier") or 0)
        proc.stdin.write((json.dumps(book, separators=(",", ":")) + "\n").encode("utf-8"))
        if stats["n"] % 100000 == 0:
            print(f"  patched {stats['n']}", flush=True)
    proc.stdin.close()
    err = proc.wait()
    if err:
        message = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", "replace")
        raise RuntimeError(f"zstd failed ({err}): {message[:400]}")
    os.replace(tmp, path)
    return stats, payouts


def update_lut_payouts(path: str, payouts: dict[int, int]) -> int:
    rows = []
    changed = 0
    with open(path, newline="", encoding="utf-8") as handle:
        for book_id, weight, cents in csv.reader(handle):
            ident = int(book_id)
            nxt = payouts.get(ident, int(cents))
            if nxt != int(cents):
                changed += 1
            rows.append((ident, int(weight), int(nxt)))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for book_id, weight, cents in rows:
            handle.write(f"{book_id},{weight},{cents}\n")
    return changed


def patch_publish_dir(publish_dir: str, modes: Iterable[str] = MODES) -> dict:
    summary = {}
    for mode in modes:
        books = os.path.join(publish_dir, f"books_{mode}.jsonl.zst")
        lut = os.path.join(publish_dir, f"lookUpTable_{mode}_0.csv")
        if not os.path.isfile(books) or not os.path.isfile(lut):
            raise FileNotFoundError(mode)
        print(f"patch {mode} books…", flush=True)
        stats, payouts = patch_books_file_stream(books)
        lut_changed = update_lut_payouts(lut, payouts)
        summary[mode] = {**stats, "lut_payouts": lut_changed}
        print(f"{mode} {summary[mode]}", flush=True)
    print("reweight LUTs…", flush=True)
    summary["weights"] = {
        mode: {
            "rtp": stats["rtp"],
            "hit_rate": stats["hit_rate"],
            "bonus_freq": stats.get("bonus_freq"),
        }
        for mode, stats in reweight_publish_dir(publish_dir, modes).items()
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Folder with books_*.jsonl.zst and lookUpTable_*_0.csv")
    parser.add_argument("--modes", nargs="+", default=list(MODES))
    args = parser.parse_args()
    print(json.dumps(patch_publish_dir(args.dir, args.modes), indent=2, default=str))


if __name__ == "__main__":
    main()
