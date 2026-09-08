# Sunset Stereo — Stake Engine publication review

Reviewed against `docs/ENGINE_DOCUMENTATION.md` (engine.io Math, Frontend, RGS, Approval).

**Current status: first Engine *test* version is ready to upload.** This is not a production math pack and is not ready for Stake review.

**Production (locked):** 6×4 left-to-right ways. 3 scatters → 10 hold-respin extra plays. No wilds, no xWays/xNudge, no Golden Hour, no buy bonus.

| Surface | Role |
| --- | --- |
| Math SDK `games/sunset_stereo/` | 6×4 ways — production rules, **1000-book test sims** |
| Player `apps/sunset-stereo/` | 6×4 Pixi client — RGS via `stake-engine`, mock books without a session |
| `publish/sunset_stereo/` | ACP math upload folder |
| `games/_inactive_sunset_stereo_5x3/` | Archived 5×3 |
| `frontend/` | Archived 5×3 DOM player |

---

## What is done for the test upload

- Compressed books + LUT + `index.json` (base mode, cost 1.0, 1000 rows).
- Payouts quantized to 0.10× so LUT values are multiples of 10.
- Player uses book events from RGS/mock. No client RNG for the bet result.
- Query params: `sessionID`, `rgs_url`, `replay`, `game`, `version`, `mode`, `event`, `social`, `currency`, `amount`.
- Replay: `GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event}` with `https://` added if the host has no protocol. Betting UI hidden. Play / Play again.
- Wallet amounts are RGS micro-units (`1.00` → `1000000`).
- Bet levels come from authenticate (mock uses a default ladder).
- Rules modal + Engine disclaimer (wins come from the RGS, not the browser).
- Social labels: Credit/Stake/Paid → Balance/Play amount/Won when `social=true`.
- Vite `base: "./"` so the static `dist` works on the Engine CDN path.

Demo subset: `apps/sunset-stereo/src/rgs/demoBooks.json` (20 books: 8 losses, 8 base wins, 4 bonus). Used on VPS/local until ACP hosts the game.

---

## What you must do to publish the first test version

You need a Stake Engine team login (ACP). Nothing in this repo can log in for you.

### 1. Create the game in ACP

1. Open the Admin Control Panel for your Engine team.
2. Create game id **`sunset_stereo`** (or match whatever id you register — then keep `games/sunset_stereo/game_config.py` `game_id` in sync).
3. Create **math version 1** and **frontend version 1**.

### 2. Upload math (test pack)

Upload the folder **`publish/sunset_stereo/`** as the math files. It must contain exactly:

| File | Role |
| --- | --- |
| `index.json` | one `base` mode, cost `1.0` |
| `books_base.jsonl.zst` | 1000 compressed books |
| `lookUpTable_base_0.csv` | `id,weight,payoutMultiplier` (cents of 1× bet) |

Do **not** upload `games/_inactive_sunset_stereo_5x3/`, `frontend/`, or any `lookUpTable_bonus_*`.

Regenerate later with:

```bash
PYTHONPATH=. python3 games/sunset_stereo/run.py
make publish-math
```

Expect ACP to report a low RTP (~31%) and failed volatility fences. That is expected: the test mix forces ~2% bonus books, which over-represents extra plays. This pack is for wiring RGS, replay, and the player — not for a 96% cert.

### 3. Upload frontend

```bash
make frontend-build
```

Upload the **contents** of `apps/sunset-stereo/dist/` (including `index.html`, `assets/`, hashed JPGs). Do not zip the `dist` folder name as an extra root if ACP expects the files at the game root.

Engine hosts:

`https://{team}.cdn.stake-engine.com/{gameId}/{version}/index.html?sessionID=…&rgs_url=…&lang=en&device=desktop`

### 4. Smoke it inside Engine

From the ACP play modal:

1. Authenticate loads balance and bet levels.
2. Spin → Play `mode: "base"` → animations from `round.state.events` → EndRound.
3. Disconnect/reload finishes an active round (the player resumes `round.active` on authenticate).
4. Replay URL (mandatory later for review):

`?replay=true&game={gameId}&version={mathVersion}&mode=base&event={bookId}&rgs_url={rgs host}`

Collect event IDs for: loss (`payout 0`), small base win, bonus trigger (freegame). There is still **no `wincap` book** in this 1000-pack.

Local / VPS without Engine still works: open the site with no query string (mock books). Replay demo: `?replay=true&event=23`.

### 5. Do **not** submit for Stake review yet

Before a real approval request you still need:

| Gap | Why |
| --- | --- |
| 100,000–1,000,000 base sims | Docs minimum for a real LUT |
| `run_optimization = True` + wincap distribution | Target 96% RTP, hit-rate, std |
| Game tiles | `SunsetStereo-BG`, `SunsetStereo-FG`, provider logo, ≤3MB |
| Audio + mute | Approval UI checklist |
| Optional i18n | English-only is allowed if other `lang` values do not break glyphs |
| Listing blurb | Theme + mechanics for the store tile |
| Wincap books | Reviewers ask for a max-win replay |

Until those land, treat ACP as a private RGS sandbox.

---

## Approval checklist vs this test build

| Rule | Test build |
| --- | --- |
| Stateless bets | Yes (books) |
| No jackpot / gamble / buy | Yes |
| RGS authenticate / play / end-round | Yes (`stake-engine`) |
| Replay | Yes |
| Disclaimer | Yes |
| Unique art | Custom JPGs + sunset scene |
| XSS / no external fonts | Yes |
| Social language | HUD swaps labels |
| 100k+ optimized math | **No** |
| Tiles / audio / UI mute | **No** |

Do not revive 5×3. Do not upload client `playRound()` as the game result — it remains only for spin-strip fillers.
