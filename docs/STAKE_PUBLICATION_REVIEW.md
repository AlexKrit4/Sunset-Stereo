# Sunset Stereo — Stake Engine publication review

Reviewed against `docs/ENGINE_DOCUMENTATION.md` (engine.io Math, Frontend, RGS, Approval) and the in-repo Math SDK (`src/`, `games/sunset_stereo/`) plus both players (`apps/sunset-stereo/`, `frontend/`).

**Verdict: not publishable on Stake yet** (no RGS, no replay, tiny unoptimized sims). Product is no longer forked.

**Production (locked):** 6×4 left-to-right ways. Scatter tease only. No wilds, no xWays/xNudge, no Golden Hour, no buy bonus.

| Surface | Role |
| --- | --- |
| Math SDK `games/sunset_stereo/` | **6×4 ways** — production math |
| Player `apps/sunset-stereo/` | **6×4 ways** Pixi — production client |
| `games/_inactive_sunset_stereo_5x3/` | Deactivated 5×3 lines + Golden Hour snapshot |
| `frontend/` | Deactivated 5×3 DOM player |

Stake is still blocked because the player rolls `playRound()` in the browser. Next work is books + RGS + replay on this 6×4 game — do not revive 5×3.

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
| Game finalized before review | No — tiny sims, no RGS, client RNG |

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
- `POST /wallet/play` then `POST /wallet/end-round` after animations (`auto_close_disabled=False` on base — OK)
- Bet levels **only** from authenticate (`minStep`, min/max)
- Amounts as **integers with 6 decimal places** (`1.00` → `1000000`)
- Official client: `github.com/engineio/ts-client`

Live HUD uses a hardcoded `[0.1 … 25]` ladder and a fake `balance: 1000`. XSS: no Google Fonts (good). Hosted build must be static files on Engine CDN only.

### 1.6 Frontend communication

| Requirement | Live 6×4 app |
| --- | --- |
| Unique assets (not Web SDK samples) | Custom JPGs + scene photo |
| Rules: all mechanics | Describes ways, no FS — now matches math |
| Max win per mode | `wincap: 55200` in player and math |
| Feature access copy | Scatter does not start extra spins — matches math |

### 1.7 Game tiles — **missing**

Need `SunsetStereo-BG.(png|jpg)`, `SunsetStereo-FG.png` (transparent), `ProviderName-Logo.png`, combined BG+FG ≤ 3MB.

### 1.8 Quality ranking risk

Docs: missing bonus depth and generic AI look → **1★, not published**.

- Live 6×4 with tease-only scatter matches “shallow / missing bonus” — Engine may ask for more depth before 2★.
- JPG photo tiles + Georgia system fonts will not score 3★.

---

## 2. Math SDK — file format & verification

### 2.1 Upload files (`math-file-format`)

`index.json` should list a single **base** mode (cost 1.0). Bonus/80× files are leftover from the inactive 5×3 package and must not be uploaded.

**Missing from `library/publish_files/` for 6×4:** compressed `books_base.jsonl.zst` generated from the new ways config.

`run.py` still has `compression = False` and 80 base sims. ACP will not publish.

CSV rows are `id,weight,payoutMultiplier` with matching integer multipliers (×100). IDs start at **0** (docs examples start at 1). Keep id consistent with `book.id`; 0 is likely accepted if unique.

### 2.2 Simulation volume

| Mode | Now | Required |
| --- | --- | --- |
| base | **80** (old 5×3 books until regen) | 100,000–1,000,000 |
| bonus | **removed** | n/a |

`wincap` distribution is still omitted. Restore before optimization.

### 2.3 Optimization

`run_optimization = False`. Fences are 0-win + basegame RTP 0.960. They have never been executed on 6×4 strips. Old LUT numbers below are from the inactive 5×3 run and are invalid.

### 2.4 Critical math tests (against current LUTs)

| Test | Need | Current |
| --- | --- | --- |
| Base mode cost 1.0, cheapest | Yes | Pass (only mode) |
| Max win ≤ 500,000× | 55200 | Pass |
| Max cost ≤ 2,000× | 1.0 | Pass |

`run_format_checks` / `execute_all_tests` is off.

### 2.5 Game logic vs Math SDK structure

`GameConfig` / `GameState` follow the SDK MRO with **ways** evaluation. No FS, no wilds.

Issues:

- `include_padding=True` → reveal board is **6 symbols/reel** (top + 4 + bottom). Frontend must mask to 4 rows.
- `frontend/js/math.js` is the inactive 5×3 client engine — do not ship.
- `apps/sunset-stereo/src/math/*` still rolls locally; Stake upload must use Python books, not this RNG.

### 2.6 Events the frontend must handle

From 6×4 ways books (once regenerated): `reveal`, `winInfo`, `setWin`, `setTotalWin`, `finalWin`, and **`wincap`** when the cap hits. No free-spin events.

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

Pixi board is **6×4 packed cells**, symbol ids `high1`/`low1` aliased to `H1`/`L1`. Math strips use `H1`–`H5`, `L1`–`L5`, `S`.

---

## 4. Recommended publication path

Do **not** upload until books + RGS exist. Product is already 6×4.

1. **Lock product** to 6×4 ways / scatter tease / no FS / cap 55200× / 96% RTP (now in `game_config.py`).
2. Restore `wincap` distribution; production sim counts; `compression = True`; `run_optimization = True`.
3. Confirm optimized RTP in 90–96.7%, hit-rate, std, max-win books. Publish `jsonl.zst` + LUT + `index.json` (base only).
4. Point `apps/sunset-stereo` at books (Web SDK or current Pixi board). No client RNG.
5. Wire `@engine.io/ts-client`, replay, currencies, RGS bet levels.
6. Rules modal: ways, RTP, max win, scatter tease, disclaimer. UI guide + mute.
7. Audio, mobile, popout, tile assets. ACP: math then frontend.

---

## 5. What is already in good shape

- Math SDK layout and class split match Engine samples.
- Production config is 6×4 ways, base-only, no wilds, scatter isolated on reels 2–5.
- No external font CDN.
- Spacebar mapped to spin.
- Theme is original enough to avoid sample-asset rejection if JPG ownership is clean.

Until books drive the Pixi board and RGS owns the wallet, none of that is sufficient for Stake.
