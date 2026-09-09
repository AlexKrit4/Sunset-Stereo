"""Copy ACP math files listed in index.json into publish/sunset_stereo/.

Keeps already-published modes when a later run only regenerated one mode
(for example bonus-only after the 1M base pack).
"""

from __future__ import annotations

import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "games", "sunset_stereo", "library", "publish_files")
DST = os.path.join(ROOT, "publish", "sunset_stereo")
MODE_ORDER = ("base", "bonus")


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

    index = {"modes": modes}
    with open(os.path.join(DST, "index.json"), "w", encoding="utf-8") as handle:
        json.dump(index, handle, indent=4)
        handle.write("\n")
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
