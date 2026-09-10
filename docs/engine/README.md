# Stake Engine docs (markdown, for agents)

This folder is the in-repo source of truth for Stake Engine. Read it instead of browsing `stake-engine.com` (SPA pages do not render as markdown) or treating `docs/ENGINE_DOCUMENTATION.md` as current.

Production game in this repo is **Sunset Stereo**: 6×4 left-to-right ways (`games/sunset_stereo/`, `apps/sunset-stereo/`). Do not revive `games/_inactive_sunset_stereo_5x3/` or `frontend/`. Do not regenerate the 1M base pack unless explicitly asked.

## Read order

1. **[HARD_RULES.md](./HARD_RULES.md)** — publish format, money units, LUT hashing, `index.json`. Break these and ACP fails (`ERR_MATH_OUTSIDE_RANGE` and similar).
2. **[math-sdk/rgs_docs/data_format.md](./math-sdk/rgs_docs/data_format.md)** — official math file format (`index.json`, LUT CSV, books `.jsonl.zst`).
3. **[math-sdk/math_docs/quickstart.md](./math-sdk/math_docs/quickstart.md)** then **[math-sdk/math_docs/overview_section/game_format.md](./math-sdk/math_docs/overview_section/game_format.md)** — how Math SDK produces those files.
4. **[rgs/RGS.md](./rgs/RGS.md)** and **[rgs/wallet.md](./rgs/wallet.md)** — frontend ↔ RGS HTTP.
5. **[rgs/ts-client.md](./rgs/ts-client.md)** — npm package `stake-engine` (`RGSClient`).
6. **[frontend/web-sdk.md](./frontend/web-sdk.md)** — optional Pixi/Svelte web SDK (this game uses a custom Vite player, not the sample monorepo).
7. **[approval.md](./approval.md)** — replay, tiles, math verification, checklist, jurisdiction/`social`.

Sunset Stereo ACP notes (some steps stale vs 95× buy-bonus): [STAKE_PUBLICATION_REVIEW.md](../STAKE_PUBLICATION_REVIEW.md).

## Layout

| Path | What it is |
| --- | --- |
| [HARD_RULES.md](./HARD_RULES.md) | Agent hard constraints learned from Engine publish + this repo |
| [SOURCES.md](./SOURCES.md) | Upstream URLs and what could not be fetched |
| [math-sdk/](./math-sdk/) | Official [StakeEngine/math-sdk](https://github.com/StakeEngine/math-sdk) `docs/` (markdown + diagrams) |
| [frontend/web-sdk.md](./frontend/web-sdk.md) | Official [StakeEngine/web-sdk](https://github.com/StakeEngine/web-sdk) README |
| [rgs/](./rgs/) | RGS HTTP, money, file format, ts-client |
| [approval.md](./approval.md) | Approval guidelines rewritten from the engine.io dump |

Math SDK frontend notes also live under [math-sdk/fe_docs/](./math-sdk/fe_docs/) and [math-sdk/fe_home.md](./math-sdk/fe_home.md). Prefer `frontend/web-sdk.md` when they overlap — it is the full current README.

The old scrape [ENGINE_DOCUMENTATION.md](../ENGINE_DOCUMENTATION.md) remains as a fallback. Prefer this folder when they disagree.
