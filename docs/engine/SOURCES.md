# Sources

In-repo markdown was assembled from public Engine/SDK docs. Live SPA pages on stake-engine.com do not yield usable markdown (empty body / 422). Prefer the GitHub markdown copies below.

## Official repositories (copied)

| Source | Copied to |
| --- | --- |
| https://github.com/StakeEngine/math-sdk `docs/` | [math-sdk/](./math-sdk/) |
| https://github.com/StakeEngine/web-sdk `README.md` | [frontend/web-sdk.md](./frontend/web-sdk.md) |
| https://github.com/StakeEngine/ts-client `README.md` + `src/` | [rgs/ts-client.md](./rgs/ts-client.md) |

Mintlify mirror of math-sdk: https://stakeengine-math-sdk.mintlify.app/  
llms.txt: https://mintlify.com/StakeEngine/math-sdk/llms.txt

## Live Engine site (not fully fetchable as markdown)

| URL | Notes |
| --- | --- |
| https://stake-engine.com/docs | SvelteKit SPA; HTML 200 with no useful body |
| https://stake-engine.com/docs/front-end | Same |
| https://stake-engine.com/docs/math/math-file-format | Same as math-sdk `rgs_docs/data_format.md` |
| https://stake-engine.com/docs/math/setup | Same as math-sdk setup/quickstart |
| https://stake-engine.com/docs/rgs | Same as math-sdk `rgs_docs/RGS.md` + wallet |
| https://stake-engine.com/docs/approval-guidelines | Rewritten into [approval.md](./approval.md) from the engine.io scrape |

Older scrape of https://engine.io/docs lives at [ENGINE_DOCUMENTATION.md](../ENGINE_DOCUMENTATION.md) (Part 1 site text, Part 2 math-sdk markdown). That dump predates some ACP errors documented in HARD_RULES.

## Package

npm `stake-engine` → GitHub `StakeEngine/ts-client`. `API_MULTIPLIER = 1_000_000`.

## What this copy dropped

- Website chrome (favicons, CSS).
- Four large Storybook PNGs (`storybook_init`, `storybook_action`, `storybook_symbols`, `storybook_add_new_book_event`) — they are UI screenshots, not API contract.
- Math SDK sample game source (not documentation).
