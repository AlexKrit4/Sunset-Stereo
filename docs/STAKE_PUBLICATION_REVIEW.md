# Sunset Stereo — Stake Engine publication review

Reviewed against `docs/ENGINE_DOCUMENTATION.md` (engine.io Math, Frontend, RGS, Approval) and the in-repo Math SDK (`src/`, `games/sunset_stereo/`) plus both players (`apps/sunset-stereo/`, `frontend/`).

**Verdict: not publishable on Stake.** ACP upload would fail math checks, and Engine review would reject the frontend. Two different games live in this repo; the deployed player does not consume RGS books.

---

## 0. Product fork (blocks everything else)

| Surface | Grid | Pays | Feature | Who decides the round |
| --- | --- | --- | --- | --- |
| Math SDK `games/sunset_stereo/` | **5×3** | **20 lines** | Golden Hour 10/14/18, wilds, Stereo Mix, buy 80× | Python books (intended) |
| README / `games/.../readme.txt` | 5×3 | 20 lines | Golden Hour | — |
| Legacy player `frontend/` | 5×3 | 20 lines | Golden Hour + buy | **Client `playRound()` RNG** |
| Live player `apps/sunset-stereo/` (port 1337) | **6×4** | **ways** | Scatter tease only, **no FS, no wilds, no buy** | **Client `playRound()` RNG** |

Stake is stateless and **precomputed**: the frontend may only animate `book.events` from `/wallet/play`. A browser RNG is an automatic reject.

**Publication target must be the Math SDK game (5×3 lines + Golden Hour).** The live 6×4 ways prototype cannot be uploaded until it has its own Math SDK package, optimized lookup tables, and a book-driven Web SDK app. Shipping 6×4 art against 5×3 books would fail replay, math verification, and rules-vs-playtest.

---

## 1. Approval guidelines — submission checklist

### 1.1 General (`approval-guidelines`)

| Rule | Status |
| --- | --- |
| Stateless: each bet independent | Math books are stateless. **Live player is not** — it rolls locally. |
| No jackpot / gamble / continuation / cashout | OK |
| Original IP, no Stake branding | Theme is original. JPG symbol art must be owned; no third-party license file in-repo. |
| Not child-appealing / not explicit | OK |
| Short theme+mechanics blurb for listing | Missing as a submission asset |
| Game finalized before review | No — two products, tiny sims, no RGS |

### 1.2 Jurisdiction / Stake US language

HUD and copy use **Credit, Stake, Paid, Spin, bet**. Restricted for `social=true` / stake.us. Need `en` plus `sweeps_en` (play amount / balance / won). English-only is allowed if other `lang` values do not corrupt glyphs.

### 1.3 Bet Replay — **mandatory, missing**

Required query params: `replay`, `game`, `version`, `mode`, `event`, `rgs_url`.

Required UX: auto-fetch `GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event}`, loader, Play, full animation, no betting UI, no session APIs, Play Again, error state, no escape into real play.

**None of this exists.** Provide reviewers with event IDs for: loss, normal win, big win, wincap, bonus trigger — current library has **zero `wincap` events**.

### 1.4 Disclaimer

Engine template required in rules popup. Current footer is a one-liner and omits: disconnect/reload, expected return over many plays, display not a physical device, **wins come from RGS not the browser**, `TM and © 2026 Engine`.

### 1.5 RGS communication — **missing**

Required:

- `rgs_url` + `sessionID` from the query string (never hardcode)
- `POST /wallet/authenticate` on load
- `POST /wallet/play` then `POST /wallet/end-round` after animations (`auto_close_disabled=False` on both modes — OK)
- Bet levels **only** from authenticate (`minStep`, min/max)
- Amounts as **integers with 6 decimal places** (`1.00` → `1000000`)
- Official client: `github.com/engineio/ts-client`

Live HUD uses a hardcoded `[0.1 … 25]` ladder and a fake `balance: 1000`. XSS: no Google Fonts (good). Hosted build must be static files on Engine CDN only.

### 1.6 Frontend communication

| Requirement | Live 6×4 app | Math-aligned `frontend/` |
| --- | --- | --- |
| Unique assets (not Web SDK samples) | Custom JPGs + scene photo | Partial |
| No visual bugs / missing anims | Prototype quality | DOM reels |
| Mini-player / popout undistorted | Viewport `min(620px, 78vw)` not tested in modal | No |
| Mobile UI usable | Partial | Partial |
| Images/fonts from Engine CDN | Bundled in Vite dist — must be uploaded with the game | — |
| Rules: all mechanics | Describes **ways, no FS** — contradicts math | Has Golden Hour in JS config, weak rules UI |
| RTP per mode | “96%” claimed, not measured | Same |
| Max win per mode | Live `wincap: 55200` vs math **5000×** | 5000 |
| Full paytable + specials | Ways table only; no wild/scatter values | Paytable in JS, not a rules modal |
| Feature access copy (3/4/5 scatters) | Explicitly says scatter does **not** start extra spins | Partial |
| UI button guide | Missing | Missing |
| Change bet + all RGS bet levels | Local list | Local list |
| Balance display | Fake credit | Fake |
| Final win clear; incremental if multiple actions | Single banner | setWin path exists but amounts are **cents×bet without /100** |
| Mute sounds | **No audio at all** — still need a mute control if SFX are added; silent games usually fail quality | None |
| Space → bet | Yes | Yes |
| Autoplay confirm | No autoplay (OK) | No |
| Network tab clean | Client RNG, no RGS | Same |
| Fast play still legible | N/A | N/A |

### 1.7 Game tiles — **missing**

Need `SunsetStereo-BG.(png|jpg)`, `SunsetStereo-FG.png` (transparent), `ProviderName-Logo.png`, combined BG+FG ≤ 3MB.

### 1.8 Quality ranking risk

Docs: missing bonus depth and generic AI look → **1★, not published**.

- Live 6×4 with tease-only scatter matches “shallow / missing bonus”.
- Math game *has* Golden Hour + Stereo Mix — that is the 2★ path if the player is rebuilt in Web SDK with polished FS intro/outro, mix meter, wild multipliers, buy-bonus confirm, audio.
- JPG photo tiles + Georgia system fonts will not score 3★.

---

## 2. Math SDK — file format & verification

### 2.1 Upload files (`math-file-format`)

`index.json` is correctly shaped (`base` cost 1.0, `bonus` cost 80.0).

**Missing from `library/publish_files/`:**

- `books_base.jsonl.zst`
- `books_bonus.jsonl.zst`

`config.json` already points at those names with **empty sha256**. `run.py` has `compression = False` and only 80/20 sims. ACP will not publish.

CSV rows are `id,weight,payoutMultiplier` with matching integer multipliers (×100). IDs start at **0** (docs examples start at 1). Keep id consistent with `book.id`; 0 is likely accepted if unique.

### 2.2 Simulation volume

| Mode | Now | Required |
| --- | --- | --- |
| base | **80** | 100,000–1,000,000 |
| bonus | **20** | same order |

`wincap` distribution is **commented out** (“small local sim”). Must be restored before optimization. No max-win books → replay/review cannot test cap.

### 2.3 Optimization

`run_optimization = False`. All LUT weights = **1**. Forced `freegame` quota 0.1 in 80 spins ⇒ ~8 huge bonus rounds dominate.

Empirical (equal weights):

- **base EV ≈ 7537% RTP** (claimed 96%)
- **bonus EV ≈ 791× / 80 cost ≈ 988% RTP**

Critical RTP band is 90.0–96.7%. This package would be rejected on sight.

Optimization fences in `game_optimization.py` look structurally valid (0-win + basegame RTP 0.599 + freegame RTP 0.360 = 0.959; bonus 0.960). They have never been executed.

### 2.4 Critical math tests (against current LUTs)

| Test | Need | Current |
| --- | --- | --- |
| Base mode cost 1.0, cheapest | Yes | Pass (1.0 vs 80) |
| Base std ≥ 0.6 | Yes | Sample std 390 (unoptimized; will change) |
| RTP 90–96.7% | Yes | **Fail** |
| Cross-mode RTP within 0.5% | Yes | Unknown until optimized |
| Max win ≤ 500,000× | 5000 | Pass |
| Max cost ≤ 2,000× | 80 | Pass |
| Non-zero hit ≥ 1/50 | base 48/80 zeros = 40% hit | Sample pass; not production |
| Wincap realistically hittable | typically < 1 in 10M | **No wincap sims** |
| Outcome diversity | 100k+ unique-enough books | 26 unique base payouts |

`run_format_checks` / `execute_all_tests` is off.

### 2.5 Game logic vs Math SDK structure

`GameConfig` / `GameState` / override / executables follow the intended MRO. Lines evaluation, scatter FS, `updateGlobalMult` for Stereo Mix, padding reveals, and event names match sample **lines** games.

Issues:

- `include_padding=True` → reveal board is **5 symbols/reel** (top + 3 + bottom). Frontend must mask to 3 rows and offset win `row` by +1 (engine already offsets `winInfo` / scatter positions).
- Wild multipliers only in freegame (`assign_mult_property`) — matches readme.
- `evaluate_wincap()` is called from line-win emit; never fired in the 100 books.
- Bonus buy still emits a **basegame** reveal then `freeSpinTrigger` — correct for this SDK.
- `frontend/js/math.js` is a **second, independent** 5×3 implementation. It must not ship; only Python books are the source of truth.
- `apps/sunset-stereo/src/math/*` is a **third** 6×4 ways engine. Do not upload it as the math package.

### 2.6 Events the frontend must handle

From current books: `reveal`, `winInfo`, `setWin`, `setTotalWin`, `finalWin`, `freeSpinTrigger`, `freeSpinRetrigger`, `updateFreeSpin`, `updateGlobalMult`, `freeSpinEnd`.

Also required when cap hits: **`wincap`**. No handler in either player.

Amounts are **integer cents of the bet multiplier** (`0.20×` → `20`). `frontend/js/main.js` does `cents * bet` **without `/100`** → 100× overstated wins. The Svelte `bookEventHandlerMap` assigns `ui.win = bookEvent.amount` the same way — and is unused.

---

## 3. Frontend SDK

Docs require a **Web SDK** app (`StakeEngine/web-sdk`): TurboRepo, Storybook, `pixi-svelte`, `utils-book`, `utils-xstate`, `components-ui-*`, `setContext()` at `+page.svelte`.

README already says: copy `apps/lines`, move Sunset board + handlers.

What exists today:

| Web SDK piece | Repo |
| --- | --- |
| `playBookEvents` sequential | Dead code in `apps/.../playBook.ts`; unused |
| `bookEventHandlerMap` | Written for 5×3 events; **spin path never calls it** |
| `eventEmitter.broadcast / broadcastAsync` | Only `broadcast`; `Promise.all` not SDK `sequence` |
| Storybook MODE_BASE / MODE_BONUS / bookEvent stories | Missing |
| RGS authenticate/play/endRound in context | Missing |
| Loading screen | Missing |
| Layout system / mini-player | Custom CSS frame |
| i18n (lingui) | Missing |
| Howler + mute | Missing |
| Bonus buy confirm | Missing in live app |

`betMachine.svelte.ts` calls `playRound()` then `board.playRound(round)` — client simulation, not books.

Pixi board is **6×4 packed cells**, symbol ids `high1`/`low1`. Math symbols are `H1`/`L1`/`W`/`S`. Art loader already aliases both, but grid and pay evaluation do not match books.

---

## 4. Recommended publication path

Do **not** upload the VPS 6×4 build.

1. **Lock product** to 5×3 / 20 lines / Golden Hour / 80× buy / 5000× cap / 96% RTP (already in `game_config.py`).
2. Restore `wincap` distribution; set `num_sim_args` to production (≥100k/mode, divisible by `threads * batching_size`); `compression = True`; `run_optimization = True`; `run_analysis = True`; `run_format_checks = True`.
3. Confirm optimized RTP in 90–96.7%, cross-mode ≤0.5%, hit-rate, std, and that max-win books exist. Copy `jsonl.zst` + LUTs + `index.json` into `publish_files/` with hashes.
4. Scaffold `apps/sunset-stereo` **inside web-sdk** (clone `apps/lines`). Consume books only. Implement every event including `wincap`. Scale amounts `/100` then × RGS bet.
5. Wire `@engine.io/ts-client`: authenticate, play, end-round, `rgs_url`/`sessionID`, currency formatters, bet levels from auth.
6. Bet Replay UX (mandatory).
7. Rules modal: full disclaimer, RTP+max win per mode, 20 lines, wild/scatter/mix, 3/4/5 → 10/14/18, retrigger 4/6/10, buy 80×. UI guide + mute. Space = play. `sweeps_en` if targeting stake.us.
8. Audio, FS intro/outro, mix meter, wild multiplier badges, payline highlights, mobile + popout.
9. Tile assets. ACP: math files then frontend static hosting.
10. Keep the 6×4 ways table as a **separate** future game (new `game_id`, new books) — do not mix it into this upload.

---

## 5. What is already in good shape

- Math SDK layout and class split match Engine samples.
- Event type names match Web SDK lines sample (`updateGlobalMult` not a custom type).
- Base cost 1.0 + buy-bonus 80.0 is a valid mode pair.
- Paytable, 20 lines, scatter isolation on strips, Stereo Mix tick after winning FS.
- No external font CDN.
- Spacebar mapped to spin.
- Theme is original enough to avoid sample-asset rejection if JPG ownership is clean.

Until books drive the Pixi board and RGS owns the wallet, none of that is sufficient for Stake.
