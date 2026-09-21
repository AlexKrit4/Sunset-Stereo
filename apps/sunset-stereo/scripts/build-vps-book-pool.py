#!/usr/bin/env python3
"""Build a weighted random book pool for the VPS mock (not packed for Stake)."""

from __future__ import annotations

import argparse
import csv
import heapq
import io
import json
import random
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import IO

DEFAULT_ZIP = "/opt/sunset-stereo/Sunset-Stereo-math.zip"
DEFAULT_OUT = "/opt/sunset-stereo/vps"
ZIP_PREFIX = "Sunset Stereo/math/"
POOL_SIZE = {
    "base": 12000,
    "scatter": 8000,
    "bonus": 2500,
    "wildbonus": 2500,
}


def load_weights(handle: IO[bytes]) -> dict[int, int]:
    text = io.TextIOWrapper(handle, encoding="utf-8", newline="")
    rows = csv.reader(text)
    header = next(rows, None)
    if not header:
        return {}
    lowered = [cell.strip().lower() for cell in header]
    try:
        id_i = lowered.index("id")
        w_i = lowered.index("weight")
    except ValueError:
        id_i, w_i = 0, 1
    weights: dict[int, int] = {}
    for row in rows:
        if len(row) <= max(id_i, w_i):
            continue
        try:
            book_id = int(float(row[id_i]))
            weight = int(float(row[w_i]))
        except ValueError:
            continue
        if book_id >= 0 and weight > 0:
            weights[book_id] = weight
    return weights


def zstd_lines(raw: IO[bytes]):
    proc = subprocess.Popen(
        ["zstd", "-d", "-c", "-T0"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin and proc.stdout

    def pump():
        assert proc.stdin
        while True:
            chunk = raw.read(1024 * 1024)
            if not chunk:
                break
            proc.stdin.write(chunk)
        proc.stdin.close()

    import threading

    worker = threading.Thread(target=pump, daemon=True)
    worker.start()
    for line in proc.stdout:
        yield line
    worker.join()
    err = proc.wait()
    if err != 0:
        message = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", "replace")
        raise RuntimeError(f"zstd failed ({err}): {message[:400]}")


def sample_mode(zf: zipfile.ZipFile, mode: str, count: int, rng: random.Random):
    lut_name = f"{ZIP_PREFIX}lookUpTable_{mode}_0.csv"
    books_name = f"{ZIP_PREFIX}books_{mode}.jsonl.zst"
    with zf.open(lut_name) as handle:
        weights = load_weights(handle)
    heap: list[tuple[float, bytes]] = []
    seen = 0
    with zf.open(books_name) as raw:
        for line in zstd_lines(raw):
            blob = line.strip()
            if not blob:
                continue
            try:
                book_id = int(json.loads(blob).get("id") or 0)
            except json.JSONDecodeError:
                continue
            weight = max(1, weights.get(book_id, 1))
            key = rng.random() ** (1.0 / weight)
            seen += 1
            item = (key, blob)
            if len(heap) < count:
                heapq.heappush(heap, item)
            elif key > heap[0][0]:
                heapq.heapreplace(heap, item)
            if seen % 100000 == 0:
                print(f"  {mode}: scanned {seen:,}", flush=True)
    rng.shuffle(heap)
    return [blob for _, blob in heap], seen


def write_pool(out_dir: Path, mode: str, lines: list[bytes]):
    jsonl = out_dir / f"{mode}.jsonl"
    index = out_dir / f"{mode}.idx.json"
    offset = 0
    entries = []
    with jsonl.open("wb") as handle:
        for blob in lines:
            row = blob + b"\n"
            entries.append({"s": offset, "n": len(row)})
            handle.write(row)
            offset += len(row)
    index.write_text(json.dumps(entries, separators=(",", ":")), encoding="utf-8")
    return jsonl.stat().st_size, len(entries)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", default=DEFAULT_ZIP)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()
    zip_path = Path(args.zip)
    out_dir = Path(args.out)
    if not zip_path.is_file():
        raise SystemExit(f"missing math zip: {zip_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    with zipfile.ZipFile(zip_path) as zf:
        for mode, count in POOL_SIZE.items():
            print(f"sampling {mode} x{count}", flush=True)
            lines, seen = sample_mode(zf, mode, count, rng)
            size, kept = write_pool(out_dir, mode, lines)
            print(f"  wrote {kept} of {seen:,} books ({size / 1_048_576:.1f} MB)", flush=True)
    print(f"pool ready at {out_dir}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
