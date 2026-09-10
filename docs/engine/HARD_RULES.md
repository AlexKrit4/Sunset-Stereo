# Stake Engine hard rules

These are non-negotiable for ACP math/frontend publish. Official wording: [rgs/data_format.md](./rgs/data_format.md). Failures below are from Engine hashing/parsing, not from the Math SDK samples.

Sunset Stereo helpers that already enforce several of these: `games/sunset_stereo/copy_publish.py`, `games/sunset_stereo/weight_bonus.py` `write_lut()`.

---

## 1. Static files only

Engine games are **precomputed**. Every outcome for a mode lives in compressed books. `/wallet/play` picks a simulation ID by LUT weight and returns that book's `events`. The browser must not roll the bet result.

Frontend build: static files only. No runtime fetches of fonts/scripts from the public internet (XSS / CDN policy). Vite `base` must be `"./"` so assets work on

`https://{team}.cdn.stake-engine.com/{gameId}/{version}/index.html?...`

Query params (never hardcode RGS host):

| Param | Role |
| --- | --- |
| `sessionID` | Required for wallet calls |
| `rgs_url` | Host only; prefix `https://` (or `http://` in local mock) |
| `lang` | ISO 639-1 |
| `device` | `mobile` or `desktop` |
| `replay` | `true` → replay mode, no session calls |
| `social` | `true` → stake.us wording |

---

## 2. `index.json`

The math upload folder must contain a file named **`index.json`**. It is **one JSON value**. Allowed shape:

```json
{
    "modes": [
        {
            "name": "base",
            "cost": 1.0,
            "events": "books_base.jsonl.zst",
            "weights": "lookUpTable_base_0.csv"
        }
    ]
}
```

Rules:

- Top-level object has **only** `modes`.
- Each mode has **only** `name`, `cost`, `events`, `weights`.
- `name` is a string (Engine play `mode` matches this, case as published).
- `cost` is a float **multiplier of the selected 1× stake**. Base mode **must** be `1.0` and the cheapest mode.
- `events` / `weights` are filenames in the **same folder** as `index.json`.
- File must be UTF-8. Write with Unix newlines. After `json.dumps`, `JSONDecoder().raw_decode` leftover must be `''` — no second JSON value, no trailing junk that parsers treat as another token.
- Do not put comments, extra keys, or a second object after the modes array.

ACP math zip layout used for Sunset Stereo:

```
Sunset Stereo/math/index.json
Sunset Stereo/math/books_base.jsonl.zst
Sunset Stereo/math/lookUpTable_base_0.csv
Sunset Stereo/math/books_bonus.jsonl.zst
Sunset Stereo/math/lookUpTable_bonus_0.csv
```

Re-download **books and LUT for a mode together**. Mixing an old LUT with new books fails the payout hash.

---

## 3. Lookup table CSV

Each mode's `weights` file: **no header**. One row per book, `uint64` columns:

```
id,weight,payoutMultiplier
```

Example:

```
1,199895486317,0
2,25668581149,20
3,126752606,140
```

Rules:

- Column 1 = book `id`.
- Column 2 = selection weight (not a float probability).
- Column 3 = `payoutMultiplier` in **cents of 1×** (see §5). Must be a **multiple of 10** if you quantize to 0.10× (Engine stats use integers).
- **Unix `\n` line endings.** Python `csv.writer` defaults to `\r\n` on some platforms. CRLF makes Engine parse column 3 differently from the books → **`ERR_MATH_OUTSIDE_RANGE`**: "lookup table CSV payouts do not match payoutMultiplier value in event file".
- Row order must match books file order. Engine extracts both payout arrays and **hashes** them. Same numbers in a different order still fail.
- `id` sequence in the LUT must match `id` sequence in the books.

Write LUT rows as:

```python
with open(path, "w", encoding="utf-8", newline="\n") as handle:
    for book_id, weight, cents in rows:
        handle.write(f"{int(book_id)},{int(weight)},{int(cents)}\n")
```

Do not use `csv.writer` unless you set `lineterminator="\n"` and verify `b"\r" not in raw`.

---

## 4. Books (`.jsonl.zst`)

Uncompressed JSONL, one object per line, then zstd. Every line **must** have:

```json
{
  "id": 1,
  "events": [{}, "..."],
  "payoutMultiplier": 1150
}
```

- `payoutMultiplier` **1150** means **11.5× of the 1× stake**, even if the mode `cost` is 95. It is **not** scaled by mode cost.
- `finalWin.amount` (or equivalent last total-win event) must equal `payoutMultiplier`.
- Mode cost 95, expected payout 90.25× of 1× → RTP = `E[payoutMultiplier/100] / 95` ≈ 0.95.
- Max size: one events file ≤ 4.2 GB; one mode ≤ 10,000,000 events.

Pretty-printed JSONL is for local inspection only. Publish files are compressed jsonl (one object per line).

---

## 5. Two money systems (do not mix)

### A. Wallet / RGS JSON (`amount`, `minBet`, `balance.amount`)

Integers with **six decimal places**. `API_MULTIPLIER = 1_000_000`.

| Integer | Display |
| --- | --- |
| 100000 | 0.10 |
| 1000000 | 1.00 |
| 10000000 | 10.00 |

Debit for a round: `baseBetAmount * mode.cost`. Example: $1.00 base (`1000000`) × bonus cost `95` → debit `95000000`.

Currency affects **display only**.

### B. Book / LUT `payoutMultiplier`

Integer **cents of 1×**. `11.5x` → `1150`. `0` → `0`. Wincap 15000× → `1500000`.

Player cash win ≈ `(payoutMultiplier / 100) * (baseBetDisplay)`.

RTP for a mode:

```
RTP = sum(weight_i * (payout_i / 100)) / sum(weight_i) / cost
```

For cost `1.0`, that is just expected 1× multiplier. For buy-bonus cost `95`, divide by 95.

---

## 6. Play / end-round

1. On load: `POST {rgs_url}/wallet/authenticate` with `sessionID`. Other wallet calls return `ERR_IS` until this succeeds.
2. `POST /wallet/play` with `{ sessionID, amount, mode }`. `amount` is the **1×** stake in micro-units, not the debit. Engine multiplies by mode cost.
3. Animate `round.state` / book `events`.
4. If the round stays `active` (typical non-zero win), call `POST /wallet/end-round` after animations. Do not start another play while a round is active.
5. `POST /bet/event` is optional progress for disconnect resume (`round.event`).

`disabledBuyFeature` from authenticate jurisdiction must hide buy-bonus UI.

Replay (`replay=true`): `GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event}`. No authenticate/play. Hide betting UI. See [approval.md](./approval.md).

---

## 7. Math gates Engine actually runs

Critical (block publish / review):

| Check | Limit |
| --- | --- |
| Base mode | cost `1.0`, cheapest |
| Base stddev | ≥ 0.6 |
| RTP per mode | 90.0%–96.7% |
| Cross-mode RTP | within 0.5% of each other |
| Max win | ≤ 500,000× |
| Max cost | ≤ 2,000× |
| Non-zero hit rate | at least 1 in 50 |
| Single events file | ≤ 4.2 GB, ≤ 10M books |

Sunset Stereo targets: RTP **95%**, wincap **15000×**, bonus cost **95×**, bonus dead mass **75%** (`payout < 95×`), recoup **25%** (`payout ≥ 95×`).

---

## 8. Frontend contract

- Wins shown to the player come from the RGS book, not from client RNG.
- Incremental win meter must end on the book total.
- Spacebar = spin (unless jurisdiction `disabledSpacebar`).
- Autoplay needs an explicit confirm; no one-click infinite spin.
- Rules must state RTP, max win, mode costs, and the Engine disclaimer (results from RGS, not the browser).
- `social=true`: replace bet/win/buy wording (see [approval.md](./approval.md)).
