# Math SDK documentation (official markdown)

Copied from [StakeEngine/math-sdk](https://github.com/StakeEngine/math-sdk) `docs/`. This is the Python simulation SDK that emits books, LUTs, and `index.json`.

Start here:

1. [index.md](./index.md) — SDK overview and static-file criteria
2. [math_docs/quickstart.md](./math_docs/quickstart.md)
3. [math_docs/directory.md](./math_docs/directory.md)
4. [math_docs/overview_section/game_format.md](./math_docs/overview_section/game_format.md)
5. [rgs_docs/data_format.md](./rgs_docs/data_format.md) — **ACP upload format**
6. [rgs_docs/RGS.md](./rgs_docs/RGS.md)

Frontend chapters in this tree ([fe_docs/](./fe_docs/), [fe_home.md](./fe_home.md)) overlap [../frontend/web-sdk.md](../frontend/web-sdk.md). Prefer the web-sdk README for current Pixi/Svelte steps.

Agent publish constraints that the SDK README does not spell out (Unix LUT, `index.json` leftover, cents vs micro-units): [../HARD_RULES.md](../HARD_RULES.md).

This repo's production math is `games/sunset_stereo/`, not the math-sdk sample games (`0_0_lines`, etc.).
