"""Copy ACP math files listed in index.json into publish/sunset_stereo/."""

from __future__ import annotations

import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "games", "sunset_stereo", "library", "publish_files")
DST = os.path.join(ROOT, "publish", "sunset_stereo")


def main() -> None:
    index_path = os.path.join(SRC, "index.json")
    with open(index_path, encoding="utf-8") as handle:
        index = json.load(handle)
    os.makedirs(DST, exist_ok=True)
    names = {"index.json"}
    for mode in index["modes"]:
        names.add(mode["events"])
        names.add(mode["weights"])
    for name in sorted(names):
        src = os.path.join(SRC, name)
        if not os.path.isfile(src):
            raise FileNotFoundError(src)
        shutil.copy2(src, os.path.join(DST, name))
        print(f"copied {name}")
    extra = [name for name in os.listdir(DST) if name not in names]
    for name in extra:
        os.remove(os.path.join(DST, name))
        print(f"removed leftover {name}")


if __name__ == "__main__":
    main()
