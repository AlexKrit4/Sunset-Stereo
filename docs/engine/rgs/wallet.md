# RGS wallet and play APIs

Official overview: [RGS.md](./RGS.md). File format: [data_format.md](./data_format.md). Client: [ts-client.md](./ts-client.md).

Authenticate **must** run on first load. Until then, play/balance/end-round return `400 ERR_IS`.

Intended basic flow: `authenticate` → `play` → animate → `end-round` if the round stays active (typical non-zero win). For long features, `POST /bet/event` stores progress; on reload, `round.event` from authenticate says where to resume.

`rgs_url` in the game URL is a **host**. Prefix `https://` unless you are on a local mock.

---

## `POST /wallet/authenticate`

```json
{ "sessionID": "xxxxxxx" }
```

ts-client also sends `language`.

Response (shape):

```json
{
  "balance": { "amount": 100000, "currency": "USD" },
  "config": {
    "minBet": 100000,
    "maxBet": 1000000000,
    "stepBet": 100000,
    "defaultBetLevel": 1000000,
    "betLevels": [],
    "jurisdiction": {
      "socialCasino": false,
      "disabledFullscreen": false,
      "disabledTurbo": false,
      "disabledSuperTurbo": false,
      "disabledAutoplay": false,
      "disabledSlamstop": false,
      "disabledSpacebar": false,
      "disabledBuyFeature": false,
      "displayNetPosition": false,
      "displayRTP": false,
      "displaySessionTimer": false,
      "minimumRoundDuration": 0
    }
  },
  "round": { }
}
```

`round` may be the active round or the last completed one. If `round.active` is true, continue that round instead of placing a new bet.

Hide buy-bonus when `disabledBuyFeature` is true.

---

## `POST /wallet/balance`

```json
{ "sessionID": "xxxxxx" }
```

Returns `{ "balance": { "amount", "currency" } }`. ts-client polls this about every 60s while idle.

---

## `POST /wallet/play`

```json
{
  "amount": 1000000,
  "sessionID": "xxxxxxx",
  "mode": "base"
}
```

- `amount` is the **1× stake** in micro-units (`1.00` → `1000000`), not the debit.
- Debit = `amount × mode.cost` from `index.json`.
- `mode` must match a published mode `name`.
- Amount must sit in `[minBet, maxBet]` and be divisible by `stepBet`. Prefer `betLevels`.

Response: `{ "balance", "round" }` where `round.state` is the book events (or equivalent) and `round.active` says whether `end-round` is still required.

ts-client refuses a second `Play` while a round is active.

---

## `POST /wallet/end-round`

```json
{ "sessionID": "xxxxxx" }
```

Credits the win and closes the round. Call after animations when `round.active` is still true. Do not call if play already closed the round (zero-win paths sometimes do).

---

## `POST /bet/event`

```json
{ "sessionID": "xxxxxx", "event": "xxxxxx" }
```

Stores in-progress animation/step for disconnect resume.

---

## Replay (no session)

```
GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event}
```

See [approval.md](../approval.md).

---

## Error codes

| Code | Meaning |
| --- | --- |
| ERR_VAL | Invalid request |
| ERR_IPB | Insufficient balance |
| ERR_IS | Invalid / timed-out session |
| ERR_ATE | Auth failed / token expired |
| ERR_GLE | Gambling limits exceeded |
| ERR_LOC | Invalid player location |
| ERR_GEN | Server error |
| ERR_MAINTENANCE | Planned maintenance |

`ERR_MATH_OUTSIDE_RANGE` is an ACP **math publish** error (LUT vs books payout hash), not a wallet code. See [HARD_RULES.md](../HARD_RULES.md).
