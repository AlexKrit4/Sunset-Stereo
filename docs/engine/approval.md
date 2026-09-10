# Approval guidelines

Rewritten from the public Engine approval pages (engine.io / stake-engine.com). Live SPA pages were not fetchable as markdown; this is the in-repo copy agents should follow. Official math file format: [data_format.md](./rgs/data_format.md). Hard publish constraints: [HARD_RULES.md](./HARD_RULES.md).

---

## General requirements

When a game is submitted, Engine technical support reviews a **specific frontend version + math version**. They inspect functionality, clarity, communication, and technical performance.

Include a short blurb describing theme and mechanics for promotional copy and the game description tag.

### Key restrictions

- **Stateless.** Each bet is independent. No jackpots, gamble features, continuation, or early cashout.
- Team names, titles, and assets must comply with IP/copyright law.
- Games must be original. Pre-purchased or licensed games that already exist on third-party sites are not permitted.
- No Stake™ branding or themes in assets.
- Approval is at reviewer discretion. Offensive, explicit, poor-taste, or low-quality games may be rejected.
- Nothing that promotes, encourages, or is likely to appeal to underage persons — including artistic depictions of children or child-like characters in a gambling context.
- Games are automatically considered for stake.us if they meet jurisdiction language rules. Test with `social=true`.

### Post-release

Submit only when the game is finalized.

After approval on Stake / Stake US, only minor visual fixes are allowed unless Engine asks otherwise. Changes to the math model, new modes, or gameplay mechanics are not allowed.

---

## Jurisdiction / social casino

For stake.us, certain gambling terms are prohibited in rules, images, and UI. Query param `social=true` / `false` marks social casino. Use a language file prefix such as `sweeps_<lang>`.

| Restricted | Replacement |
| --- | --- |
| win feature | play feature |
| pay out / pays out | win / won |
| paid out / paid | won |
| stake | play amount |
| betting | play / playing |
| total bet | total play |
| bet / bets | play / plays |
| cash / money | coins |
| payer | winner |
| pay / pays | win / wins |
| buy / purchase / bonus buy | play / bonus / feature |
| bought | instantly triggered |
| at the cost of / cost of | for / can be played for |
| rebet | respin |
| credit | balance |
| gamble / wager | play |
| deposit | get coins |
| withdraw | redeem |
| currency | token |
| fund | balance |
| place your bets | come and play / join in the game |
| buy bonus | get bonus |

---

## Bet replay (mandatory)

Replay is required for new games. Reviewers will test it and ask for event IDs covering loss, normal win, big win, max win, and bonus trigger.

**No player session is required.** Replay URLs are shareable.

### Query parameters

| Param | Required | Description |
| --- | --- | --- |
| `replay` | yes | always `true` in replay mode |
| `game` | yes | game id |
| `version` | yes | math version |
| `mode` | yes | bet mode |
| `event` | yes | simulation id |
| `rgs_url` | yes | RGS host |
| `currency` | no | |
| `amount` | no | bet in micro-units |
| `lang` | no | |
| `device` | no | |
| `social` | no | |

### Fetch

```
GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event}
```

Example: `GET https://rgs.stake-engine.com/bet/replay/<uuid>/1/SUPER/55`

Response:

```json
{
  "payoutMultiplier": 25.0,
  "costMultiplier": 1.0,
  "state": {}
}
```

If `rgs_url` has no scheme, prefix `https://`.

### UX

- Auto-load the event; show **Play** once ready.
- Play full animations. Hide/disable all betting UI. No authenticate/play/end-round.
- After: **Play again**, keep final win visible.
- Hide balance/autoplay; keep win amount, currency, replay bet amount.
- No path from replay into a real session.
- Show an error if the fetch fails.

---

## General disclaimer

Rules popup must say that results come from the RGS, not the browser. Template:

> Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Engine.

---

## RGS communication

- Authenticate first. Respect `minBet`, `maxBet`, `stepBet`, and `betLevels` from the response.
- Game build is static files only. No external font/script downloads (XSS / CDN).
- Use `rgs_url` from the query string. Do not hardcode the RGS host.
- English is the only required language. Other `lang` values must not corrupt on-screen text.

Languages: `ar`, `de`, `en`, `es`, `fi`, `fr`, `hi`, `id`, `ja`, `ko`, `pl`/`po`, `pt`, `ru`, `tr`, `zh`, `vi` (plus `da` on some pages).

Currencies: see [rgs/RGS.md](./rgs/RGS.md). Social: `XGC`, `XSC`, `XEC`.

---

## Submission checklist

Incomplete submissions delay the shared review queue.

After submit, three reviewers rate design, gameplay, and math 0–3 stars (hidden until all three land).

- Average **≥ 1 star** → approved for production.
- Average **< 1 star** → rejected; you may resubmit after fixes.

---

## Frontend communication

- Unique audio/visual assets. Sample web-sdk backgrounds/symbols/animations will not be approved.
- No broken or missing assets.
- Mini-player / popout: board must not look distorted.
- Mobile: UI remains usable while scaling.
- Images and fonts from the Engine CDN only.
- Rules must cover: all mechanics, each mode's cost, RTP per mode, max win per mode, paytable, special-symbol values, how features trigger (example: “3 scatters award 10 extra plays”).
- UI guide for buttons. Player can change bet size and use **all** authenticate bet levels.
- Show balance. Show final win for non-zero results. Multi-step wins must increment to the book total.
- Mute control. Spacebar = bet (unless jurisdiction disables it).
- Autoplay requires explicit confirm — no one-click consecutive bets.
- Network tab: no errors, no leaking game internals.
- Fast-play still leaves wins, combinations, and popups legible.
- Test currencies and languages.

---

## Game quality rankings

| Rank | Meaning | Visibility |
| --- | --- | --- |
| ★★★ | Studio quality, unique, detailed | Burst / Exclusives / featured New Releases |
| ★★ | Strong originality, less polish | Burst/Exclusives if popular; New Releases if space |
| ★ | Meets publish bar but low polish | Not published; resubmit |

Common 1-star causes: shallow 1–2 spin gameplay, generic AI art, mismatched styles, missing features.

3-star: tested devices, small bundle, cohesive art, Burst concepts with real depth.

New Releases: 2+ stars get the tag; 3-star games get featured placement.

---

## Game tile assets

Combined background + foreground ≤ 3 MB.

| Asset | Spec | Name |
| --- | --- | --- |
| Background | High-res PNG/JPG, environment | `GameTitle-BG.png` |
| Foreground | High-res PNG, transparent, character/item | `GameTitle-FG.png` |
| Provider logo | High-res PNG, transparent, legible small | `ProviderName-Logo.png` |

---

## Math verification

### Bet-level templates / exposure

A bet is rejected (`400` invalid bet amount) if:

- total bet cost exceeds **$500,000 USD** equivalent, or
- potential payout from a single bet exceeds **$50,000,000 USD** equivalent.

Templates range from $1 to $1000 USD base, assigned from max cost, max payout, and volatility/risk.

### File size

- One `.jsonl.zst` ≤ **4.2 GB**
- One mode ≤ **10,000,000** events

### Summary statistics

- Mode cost matches the rules.
- RTP **90.0%–96.70%**. Across modes, RTP within **0.5%** of each other (96.0% base → others 95.5–96.5%).
- Max win matches the rules and is realistically obtainable (typically more frequent than 1 in 10,000,000, depending on size).
- Slots: 100k–1M simulations for diversity.
- A reasonable share of simulations should pay (90k zeros out of 100k may be rejected).
- The most likely single simulation must not dominate if the UI implies variety.

### Critical tests (block)

| Test | Requirement |
| --- | --- |
| Base mode | cost `1.0×`, cheapest mode |
| Base volatility | stddev ≥ 0.6 |
| RTP band | every mode 90.0%–96.7% |
| Cross-mode RTP | ≤ 0.5% spread |
| Max payout | ≤ 500,000× |
| Max cost | ≤ 2,000× |
| Non-zero hit rate | ≥ 1 in 50 |
| Viable bet template | at least one template fits |

### Non-critical tests (shrink bet caps)

Failing these does not block submit; it reduces maximum exposure and maximum bet cost. Related checks collapse into **six failure classes**.

Limits per rating:

| Check | 2-Star | 3-Star |
| --- | --- | --- |
| Maximum exposure | $15,000,000 | $50,000,000 |
| Maximum bet cost | $100,000 | $500,000 |
| Maximum payout multiplier | 50,000× | 100,000× |
| Maximum cost multiplier | 1,000× | 2,000× |
| Maximum base stddev | 50.0 | 60.0 |
| CVaR (per-stake) | 700 | 700 |
| CVaR (absolute) | 20,000 | 50,000 |
| P(≥ 5,000×) | 0.010 | 0.050 |
| P(≥ 10,000×) | 0.005 | 0.010 |
| ETL (> 40×) | 0.8 | 0.9 |
| ETL (> 10,000×) | 0.6 | 0.8 |
| ETL sum | 1.3 | 1.5 |

Failure classes: max payout, cost multiplier, base volatility, CVaR, ETL, tail probability. Several checks in one class count once.

2-Star exposure/bet after N failed classes:

| Failed | Exposure | Bet cost |
| --- | --- | --- |
| 0–1 | $15,000,000 | $100,000 |
| 2 | $10,000,000 | $50,000 |
| 3 | $5,000,000 | $50,000 |
| 4 | $1,000,000 | $10,000 |
| 5 | $500,000 | $10,000 |
| 6 | $100,000 | $5,000 |

3-Star:

| Failed | Exposure | Bet cost |
| --- | --- | --- |
| 0 | $50,000,000 | $500,000 |
| 1 | $25,000,000 | $500,000 |
| 2 | $15,000,000 | $250,000 |
| 3 | $10,000,000 | $100,000 |
| 4 | $5,000,000 | $50,000 |
| 5 | $1,000,000 | $10,000 |
| 6 | $500,000 | $10,000 |

A template is valid if worst-case payout (`maxWin × maxBet`) stays under exposure and worst-case cost (`maxCost × maxBet`) stays under bet-cost cap.

**Tail probability:** raw P(round ≥ 5,000× or 10,000×), not scaled by cost. Worst mode wins.

**CVaR:** expected payout in the worst 0.1%. Per-stake = CVaR / cost (limit 700). Absolute limits 20k / 50k.

**ETL:** share of mode RTP from heavy tails, normalized by cost.

Also inspect: non-zero hit rate ≥ 1/50, base stddev in industry range, zero-weight rows not dominating, no empty win-range gaps between small pays and max win.
