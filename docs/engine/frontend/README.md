# Frontend SDK

Sunset Stereo's player is the custom Vite app in `apps/sunset-stereo/`, talking to RGS via `stake-engine`. It is **not** a fork of the sample TurboRepo.

Still follow:

- Vite `base: "./"`
- Query `sessionID`, `rgs_url`, `lang`, `device`, `replay`, `social`
- Static-only build (no external fonts)
- [../rgs/ts-client.md](../rgs/ts-client.md) and [../HARD_RULES.md](../HARD_RULES.md)

## Official web SDK (optional)

Full README from [StakeEngine/web-sdk](https://github.com/StakeEngine/web-sdk): [web-sdk.md](./web-sdk.md).

Shorter copies that shipped inside math-sdk: [../math-sdk/fe_home.md](../math-sdk/fe_home.md) and [../math-sdk/fe_docs/](../math-sdk/fe_docs/).

Sample games in that monorepo (`lines`, etc.) are not this product. Do not upload their assets.
