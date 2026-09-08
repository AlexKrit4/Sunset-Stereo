export const GAME = {
  id: "sunset_stereo",
  name: "Sunset Stereo",
  rtp: 0.96,
  wincap: 55200,
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
export const SCATTER_REEL_LAND_CHANCE = 0.11;

export const WAYS_TEASE_INTER_REEL_MS = 500;
export const WAYS_TEASE_MIN_REELS = 3;
export const SCATTER_TEASE_TOTAL_MS = 6000;
export const SCATTER_TEASE_SLOW_MS = 2000;
export const SCATTER_TEASE_ENTER_MS = 680;
export const SCATTER_TEASE_STOP_MS = 920;
export const SCATTER_TEASE_CELL_MS = 1000;
export const XNUDGE_CLUSTER_STRIP_CHANCE = 0.06;

export const PAYOUTS = {
  high1: { 3: 0.88, 4: 3, 5: 6, 6: 20 },
  high2: { 3: 0.4, 4: 0.6, 5: 3.2, 6: 10 },
  high3: { 3: 0.32, 4: 0.52, 5: 1.6, 6: 4.8 },
  high4: { 3: 0.28, 4: 0.48, 5: 1.2, 6: 4 },
  high5: { 3: 0.28, 4: 0.4, 5: 0.88, 6: 3.2 },
  low1: { 3: 0.24, 4: 0.36, 5: 0.8, 6: 2.8 },
  low2: { 3: 0.24, 4: 0.36, 5: 0.72, 6: 2.8 },
  low3: { 3: 0.2, 4: 0.32, 5: 0.68, 6: 2 },
  low4: { 3: 0.2, 4: 0.28, 5: 0.6, 6: 2 },
  low5: { 3: 0.2, 4: 0.24, 5: 0.52, 6: 1.4 },
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
