import type { BookEvent, Position, RawSymbol } from "./typesBookEvent";

export type { BookEvent, BookEventOfType, Position, RawSymbol } from "./typesBookEvent";

export type BookEventContext = { bookEvents: BookEvent[] };

export type EmitterEvent =
  | { type: "revealBoard"; board: RawSymbol[][]; gameType: "basegame" | "freegame"; anticipation: number[] }
  | { type: "boardLand"; gameType: "basegame" | "freegame" }
  | { type: "winShow"; positions: Position[] }
  | { type: "winClear" }
  | { type: "scatterShow"; positions: Position[] }
  | { type: "featureStart"; total: number }
  | { type: "featureEnd"; amount: number }
  | { type: "mixUpdate"; value: number }
  | { type: "fsUpdate"; current: number; total: number }
  | { type: "toast"; text: string };
