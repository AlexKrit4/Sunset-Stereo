# RGS example (fifty-fifty)

From the Engine RGS example page. Full API: [wallet.md](./wallet.md).

## Game

Call `/wallet/play`. Outcome is 50/50: **2×** the bet back, or lose the **1×** bet. If the win is greater than 0, the frontend must call `/wallet/end-round` after the result is shown.

## Math

In math-sdk `games/fifty_fifty/`, `run.py` writes:

- zstd books
- lookup table
- `index.json`

Publish files land in `library/publish_files/`.

## Frontend

Static Vite + Svelte 5. `vite.config` must set `base: "./"`. Upload `dist/` as frontend files.

The sample:

1. Authenticates
2. Calls play
3. Calls end-round when the win is > 0

Place BET fills the play response. END ROUND finalizes a win and updates balance.
