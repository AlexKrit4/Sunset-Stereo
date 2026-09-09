export const GAME = {
  id: "sunset_stereo",
  name: "Sunset Stereo",
  rtp: 0.95,
  wincap: 15000,
};

export const REEL_ROWS = [4, 4, 4, 4, 4, 4];
export const NUM_REELS = 6;
export const MAX_ROWS = 4;

export const XWAYS_REELS = [];
export const XNUDGE_REELS = [];
export const SCATTER_REELS = [1, 2, 3, 4];

export const XWAYS_REDUCTION = 12;
export const XNUDGE_STACK_SIZE = 4;
export const XNUDGE_LAND_CHANCE = 0.14;
export const SCATTER_WEIGHT = 0.22;
export const SCATTER_REEL_LAND_CHANCE = 0.12;
export const BONUS_SCATTER_COUNT = 3;
export const BONUS_SPINS = 10;
export const MAX_HOLD_RESPINS = 16;

export const WAYS_TEASE_INTER_REEL_MS = 500;
export const WAYS_TEASE_MIN_REELS = 3;
export const SCATTER_TEASE_TOTAL_MS = 6000;
export const XNUDGE_CLUSTER_STRIP_CHANCE = 0.06;

export const PAYOUTS = {
  high1: { 3: 0.9, 4: 3, 5: 6, 6: 20 },
  high2: { 3: 0.4, 4: 0.6, 5: 3.2, 6: 10 },
  high3: { 3: 0.3, 4: 0.5, 5: 1.6, 6: 4.8 },
  high4: { 3: 0.3, 4: 0.5, 5: 1.2, 6: 4 },
  high5: { 3: 0.3, 4: 0.4, 5: 0.9, 6: 3.2 },
  low1: { 3: 0.2, 4: 0.4, 5: 0.8, 6: 2.8 },
  low2: { 3: 0.2, 4: 0.4, 5: 0.7, 6: 2.8 },
  low3: { 3: 0.2, 4: 0.3, 5: 0.7, 6: 2 },
  low4: { 3: 0.2, 4: 0.3, 5: 0.6, 6: 2 },
  low5: { 3: 0.2, 4: 0.2, 5: 0.5, 6: 1.4 },
};

export const PAYABLE = Object.keys(PAYOUTS);

export const SYMBOLS = [
  "low1",
  "low2",
  "low3",
  "low4",
  "low5",
  "high1",
  "high2",
  "high3",
  "high4",
  "high5",
  "scatter",
];

export const BETS = [0.1, 0.2, 0.5, 1, 2, 5, 10, 25];
