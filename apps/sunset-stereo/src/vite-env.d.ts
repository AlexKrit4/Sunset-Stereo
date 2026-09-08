/// <reference types="svelte" />
/// <reference types="vite/client" />

declare module "*.js" {
  export const GAME: {
    id: string;
    name: string;
    rows: number;
    reels: number;
    wincap: number;
    rtp: number;
    buyBonusCost: number;
  };
  export const PAYTABLE: Record<string, Record<number, number>>;
  export const PAYLINES: Record<string, number[]>;
  export const FREESPINS: Record<string, Record<number, number>>;
  export const BETS: number[];
  export const SYMBOLS: Record<string, { label: string; short: string; kind: string }>;
  export function getWinLevel(winAmount: number, key?: string): number;
  export function toCents(amount: number): number;
  export function playRound(opts?: { seed?: number; buyBonus?: boolean }): {
    id: number;
    payoutMultiplier: number;
    events: import("./game/typesBookEvent").BookEvent[];
    criteria: string;
    baseGameWins: number;
    freeGameWins: number;
  };
}
