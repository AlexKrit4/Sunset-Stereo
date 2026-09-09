/**
 * Stake Engine bookEvent types for Sunset Stereo.
 * Drop this into a Web SDK app (apps/sunset-stereo/src/game/typesBookEvent.ts).
 */

export type Position = { reel: number; row: number };

export type BookEventReveal = {
  index: number;
  type: "reveal";
  board: Array<Array<{ name: string; wild?: boolean; scatter?: boolean; multiplier?: number }>>;
  paddingPositions: number[];
  gameType: "basegame" | "freegame";
  anticipation: number[];
};

export type BookEventWinInfo = {
  index: number;
  type: "winInfo";
  totalWin: number;
  wins: Array<{
    symbol: string;
    kind: number;
    win: number;
    positions: Position[];
    meta: {
      lineIndex: number;
      multiplier: number;
      winWithoutMult: number;
      globalMult: number;
      lineMultiplier: number;
    };
  }>;
};

export type BookEventSetWin = {
  index: number;
  type: "setWin";
  amount: number;
  winLevel: number;
};

export type BookEventSetTotalWin = {
  index: number;
  type: "setTotalWin";
  amount: number;
};

export type BookEventFreeSpinTrigger = {
  index: number;
  type: "freeSpinTrigger";
  totalFs: number;
  positions: Position[];
};

export type BookEventFreeSpinRetrigger = {
  index: number;
  type: "freeSpinRetrigger";
  totalFs: number;
  positions: Position[];
};

export type BookEventUpdateFreeSpin = {
  index: number;
  type: "updateFreeSpin";
  amount: number;
  total: number;
};

export type BookEventUpdateGlobalMult = {
  index: number;
  type: "updateGlobalMult";
  globalMult: number;
};

export type BookEventFreeSpinEnd = {
  index: number;
  type: "freeSpinEnd";
  amount: number;
  winLevel: number;
};

export type BookEventFinalWin = {
  index: number;
  type: "finalWin";
  amount: number;
};

export type BookEvent =
  | BookEventReveal
  | BookEventWinInfo
  | BookEventSetWin
  | BookEventSetTotalWin
  | BookEventFreeSpinTrigger
  | BookEventFreeSpinRetrigger
  | BookEventUpdateFreeSpin
  | BookEventUpdateGlobalMult
  | BookEventFreeSpinEnd
  | BookEventFinalWin;

export type BookEventOfType<T extends BookEvent["type"]> = Extract<BookEvent, { type: T }>;
