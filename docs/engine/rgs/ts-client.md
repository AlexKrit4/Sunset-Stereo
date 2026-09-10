# npm package `stake-engine` (ts-client)

Source: [StakeEngine/ts-client](https://github.com/StakeEngine/ts-client). Live API docs: https://stake-engine.com/docs/rgs (same contract as [RGS.md](./RGS.md) / [wallet.md](./wallet.md)).

```bash
npm install stake-engine
```

## Construct

```typescript
import { RGSClient } from 'stake-engine';

const rgsClient = RGSClient({
  url: window.location.href, // must contain sessionID + rgs_url
  // enforceBetLevels: true,  // default true
  // protocol: 'https',       // default https; local mock may need http
});
```

The client reads `sessionID`, `lang`, `device`, and `rgs_url` from `url`. Missing `sessionID` or `rgs_url` throws. `device` must be `desktop` or `mobile`.

RGS base URL becomes `{protocol}://{rgs_url}`.

## Methods

| Method | HTTP | Notes |
| --- | --- | --- |
| `Authenticate()` | `POST /wallet/authenticate` | body `{ sessionID, language }` |
| `Play({ amount, mode })` | `POST /wallet/play` | `amount` in micro-units (`1 * API_MULTIPLIER`) |
| `EndRound()` | `POST /wallet/end-round` | only if a round is still active |
| `Event(eventValue)` | `POST /bet/event` | disconnect resume marker |

`Play` checks: authenticated, no active round, amount in `[minBet, maxBet]`, multiple of `stepBet`, and (if `enforceBetLevels`) listed in `betLevels`. On HTTP error it clears the local active-round flag.

Idle balance refresh: about every **60 seconds** after play/end-round.

## Window events

```typescript
window.addEventListener('balanceUpdate', (event: Event) => {
  const { amount, currency } = (event as CustomEvent<{ amount: number; currency: string }>).detail;
});

window.addEventListener('roundActive', (event: Event) => {
  const { active } = (event as CustomEvent<{ active: boolean }>).detail;
});
```

Use `roundActive` to disable spin while a round is open.

Note: some README snippets say `balanceUpdated`; the client dispatches **`balanceUpdate`**.

## Helpers

```typescript
API_MULTIPLIER === 1_000_000
ParseAmount(1_000_000) === 1
DisplayAmount(balance, { removeSymbol, decimals, trimDecimalForIntegers })
```

`DisplayAmount` divides by `API_MULTIPLIER` then formats. Book `payoutMultiplier` is **not** in this unit — see [HARD_RULES.md](../HARD_RULES.md) §5.

## Types (from `src/types.ts`)

```typescript
type Balance = { amount: number; currency: Currency };

type JurisdictionFlags = {
  socialCasino: boolean;
  disabledFullscreen: boolean;
  disabledTurbo: boolean;
  disabledSuperTurbo: boolean;
  disabledAutoplay: boolean;
  disabledSlamstop: boolean;
  disabledSpacebar: boolean;
  disabledBuyFeature: boolean;
  displayNetPosition: boolean;
  displayRTP: boolean;
  displaySessionTimer: boolean;
  minimumRoundDuration: number;
};

type AuthenticateConfig = {
  minBet: number;
  maxBet: number;
  stepBet: number;
  defaultBetLevel: number;
  betLevels: number[];
};

type Round = {
  betID: number;
  amount?: number;
  payout?: number;
  payoutMultiplier?: number;
  active: boolean;
  mode: string;
  event?: string;
  state: unknown;
};

type PlayParameters = { amount: number; mode: string };
```

Languages: `ar de en es fi fr hi id ja ko pl pt ru tr vi zh`.

Currencies include fiat plus `XGC` / `XSC` (social). The approval scrape lists additional codes (`XEC`, `NGN`, …) for display; the published client type union is narrower — format unknown codes as `"{amount} {code}"`.
