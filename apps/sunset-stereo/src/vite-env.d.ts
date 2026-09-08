/// <reference types="svelte" />
/// <reference types="vite/client" />

declare module "*.js" {
  export const GAME: {
    id: string;
    name: string;
    rtp: number;
    wincap: number;
  };
  export const REEL_ROWS: number[];
  export const NUM_REELS: number;
  export const MAX_ROWS: number;
  export const XWAYS_REELS: number[];
  export const XNUDGE_REELS: number[];
  export const SCATTER_REELS: number[];
  export const PAYOUTS: Record<string, Record<number, number>>;
  export const PAYABLE: string[];
  export const SYMBOLS: string[];
  export const BETS: number[];
  export const BONUS_SPINS: number;
  export const BONUS_SCATTER_COUNT: number;
  export const MAX_HOLD_RESPINS: number;
  export const SCATTER_REEL_LAND_CHANCE: number;
  export function playRound(opts?: { seed?: number; bet?: number }): {
    raw: string[][];
    resolved: string[][];
    mults: number[][];
    reelNudgeMult: number[];
    stacks: Array<{ reel: number; visible: number }>;
    xWays: {
      positions: Array<{ reel: number; row: number; replacement: string; mult: number }>;
      replacement: string;
    };
    nudge: Array<{ reel: number; landVisible: number; nudges: number; mult: number }>;
    extraStopMs: number[];
    waysGaps: number[];
    scatterGaps: number[];
    scatterHit: number[];
    scatterCount: number;
    scatterPositions: Array<{ reel: number; row: number }>;
    bonusAwarded: number;
    bonusSpins: Array<{
      steps: Array<{
        board: string[][];
        isRespin: boolean;
        locked: Array<{ reel: number; row: number }>;
        totalWin: number;
        totalWays: number;
        wins: Array<{ sym: string; reelsMatched: number; ways: number; nudgeLineMult: number; win: number }>;
        highlights: Array<{ reel: number; row: number }>;
      }>;
      paidWin: number;
      totalWays: number;
      wins: Array<{ sym: string; reelsMatched: number; ways: number; nudgeLineMult: number; win: number }>;
      highlights: Array<{ reel: number; row: number }>;
    }>;
    bonusWin: number;
    baseWin: number;
    bet: number;
    totalWin: number;
    totalWays: number;
    wins: Array<{ sym: string; reelsMatched: number; ways: number; nudgeLineMult: number; win: number }>;
    highlights: Array<{ reel: number; row: number }>;
  };
  export function getReelRows(reel: number): number;
  export function getXNudgeVisibleCount(symbols: string[]): number;
  export function cloneGrid(grid: string[][]): string[][];
  export function pickStripSymbol(
    rng: { random: () => number; randomInt: (min: number, max: number) => number },
    reelIndex: number,
  ): string;
  export function pickStripItems(
    rng: { random: () => number; randomInt: (min: number, max: number) => number },
    reelIndex: number,
    count: number,
  ): string[];
  export function getWaysTeaseSymbol(board: string[][], upToReelInclusive: number): string | null;
  export function reelMatchesWaysTease(board: string[][], reel: number, sym: string): boolean;
}
