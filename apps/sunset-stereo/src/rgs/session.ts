import { RGSClient } from "stake-engine";
import type { AuthenticateResponse, PlayResponse, EndRoundResponse, Round } from "stake-engine";
import demo from "./demoBooks.json";
import { API_MULTIPLIER } from "./money";
import { isLiveSession, readEngineQuery, rgsOrigin, type EngineQuery } from "./query";
import type { BookEvent } from "../game/typesBookEvent";

export type BookState = {
  id: number;
  events: BookEvent[];
  payoutMultiplier: number;
  criteria?: string;
};

const DEFAULT_LEVELS = [0.1, 0.2, 0.5, 1, 2, 5, 10, 25].map((value) => value * API_MULTIPLIER);

const DEFAULT_FLAGS = {
  socialCasino: false,
  disabledFullscreen: false,
  disabledTurbo: false,
  disabledSuperTurbo: false,
  disabledAutoplay: false,
  disabledSlamstop: false,
  disabledSpacebar: false,
  disabledBuyFeature: true,
  displayNetPosition: false,
  displayRTP: true,
  displaySessionTimer: false,
  minimumRoundDuration: 0,
};

function asBook(state: unknown, fallbackMult = 0): BookState {
  const raw = state as Record<string, unknown> | BookEvent[] | null;
  if (!raw) throw new Error("Round has no math state.");
  if (Array.isArray(raw)) {
    return { id: 0, events: raw as BookEvent[], payoutMultiplier: fallbackMult };
  }
  if (Array.isArray(raw.events)) {
    return {
      id: Number(raw.id ?? 0),
      events: raw.events as BookEvent[],
      payoutMultiplier: Number(raw.payoutMultiplier ?? fallbackMult),
    };
  }
  throw new Error("Unexpected RGS round state.");
}

function createMockClient() {
  const books = (demo as { books: BookState[] }).books;
  let balance = 1000 * API_MULTIPLIER;
  let active: Round | null = null;
  let nextIndex = 0;

  return {
    kind: "mock" as const,
    async Authenticate(): Promise<AuthenticateResponse> {
      return {
        balance: { amount: balance, currency: "USD" },
        config: {
          minBet: DEFAULT_LEVELS[0],
          maxBet: DEFAULT_LEVELS[DEFAULT_LEVELS.length - 1],
          stepBet: DEFAULT_LEVELS[0],
          defaultBetLevel: API_MULTIPLIER,
          betLevels: DEFAULT_LEVELS,
        },
        jurisdictionFlags: { ...DEFAULT_FLAGS },
        round: active,
      };
    },
    async Play({ amount, mode }: { amount: number; mode: string }): Promise<PlayResponse> {
      if (active?.active) throw new Error("A round is already active.");
      if (amount > balance) throw new Error("Not enough credit.");
      balance -= amount;
      const book = books[nextIndex % books.length] ?? books[0];
      nextIndex += 1;
      const payout = Math.round((book.payoutMultiplier / 100) * amount);
      active = {
        betID: Date.now(),
        amount,
        payout,
        payoutMultiplier: book.payoutMultiplier / 100,
        active: true,
        mode,
        state: book,
      };
      return { balance: { amount: balance, currency: "USD" }, round: active };
    },
    async EndRound(): Promise<EndRoundResponse> {
      if (active?.payout) balance += active.payout;
      active = null;
      return { balance: { amount: balance, currency: "USD" } };
    },
  };
}

export type EngineHandle = {
  kind: "live" | "mock";
  query: EngineQuery;
  Authenticate: () => Promise<AuthenticateResponse>;
  Play: (params: { amount: number; mode: string }) => Promise<PlayResponse>;
  EndRound: () => Promise<EndRoundResponse>;
  bookFromRound: (round: Round) => BookState;
};

export function createEngineHandle(): EngineHandle {
  const query = readEngineQuery();
  if (isLiveSession(query)) {
    const client = RGSClient({ url: window.location.href });
    return {
      kind: "live",
      query,
      Authenticate: () => client.Authenticate(),
      Play: (params) => client.Play(params),
      EndRound: () => client.EndRound(),
      bookFromRound: (round) => asBook(round.state, Math.round((round.payoutMultiplier ?? 0) * 100)),
    };
  }
  const mock = createMockClient();
  return {
    kind: "mock",
    query,
    Authenticate: () => mock.Authenticate(),
    Play: (params) => mock.Play(params),
    EndRound: () => mock.EndRound(),
    bookFromRound: (round) => asBook(round.state, Math.round((round.payoutMultiplier ?? 0) * 100)),
  };
}

export async function fetchReplayBook(query: EngineQuery): Promise<BookState> {
  if (query.rgsUrl) {
    if (!query.game || !query.event) {
      throw new Error("Replay URL is missing game or event.");
    }
    const url = `${rgsOrigin(query.rgsUrl)}/bet/replay/${query.game}/${query.version || "1"}/${query.mode}/${query.event}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Replay failed (${res.status}).`);
    const body = (await res.json()) as { payoutMultiplier?: number; state?: unknown };
    return asBook(body.state ?? body, Math.round((body.payoutMultiplier ?? 0) * 100));
  }
  const books = (demo as { books: BookState[] }).books;
  const found = books.find((book) => String(book.id) === String(query.event));
  if (!found) {
    throw new Error(query.event ? `Replay book ${query.event} is not in the demo set.` : "Replay needs rgs_url or a demo event id.");
  }
  return found;
}
