export const GAME = {
  id: "sunset_stereo",
  name: "Sunset Stereo",
  rows: 3,
  reels: 5,
  wincap: 5000,
  rtp: 0.96,
  buyBonusCost: 80,
};

export const PAYTABLE = {
  W: { 5: 80, 4: 25, 3: 12 },
  H1: { 5: 80, 4: 25, 3: 12 },
  H2: { 5: 25, 4: 8, 3: 4 },
  H3: { 5: 15, 4: 5, 3: 2.5 },
  H4: { 5: 10, 4: 3, 3: 1.5 },
  L1: { 5: 6, 4: 1.5, 3: 0.6 },
  L2: { 5: 4, 4: 1, 3: 0.4 },
  L3: { 5: 3, 4: 0.8, 3: 0.3 },
  L4: { 5: 2, 4: 0.5, 3: 0.2 },
  L5: { 5: 1.5, 4: 0.4, 3: 0.15 },
};

export const PAYLINES = {
  1: [0, 0, 0, 0, 0],
  2: [1, 1, 1, 1, 1],
  3: [2, 2, 2, 2, 2],
  4: [0, 1, 2, 1, 0],
  5: [2, 1, 0, 1, 2],
  6: [0, 0, 1, 2, 2],
  7: [2, 2, 1, 0, 0],
  8: [1, 0, 1, 2, 1],
  9: [1, 2, 1, 0, 1],
  10: [0, 1, 1, 1, 2],
  11: [2, 1, 1, 1, 0],
  12: [0, 1, 0, 1, 2],
  13: [2, 1, 2, 1, 0],
  14: [1, 1, 0, 1, 1],
  15: [1, 1, 2, 1, 1],
  16: [0, 2, 1, 0, 2],
  17: [2, 0, 1, 2, 0],
  18: [0, 0, 2, 0, 0],
  19: [2, 2, 0, 2, 2],
  20: [1, 0, 0, 0, 1],
};

export const FREESPINS = {
  basegame: { 3: 10, 4: 14, 5: 18 },
  freegame: { 3: 4, 4: 6, 5: 10 },
};

export const BETS = [0.2, 0.4, 1, 2, 5, 10, 20, 50];

export const SYMBOLS = {
  H1: { label: "VINYL", short: "H1", kind: "high" },
  H2: { label: "CANS", short: "H2", kind: "high" },
  H3: { label: "TAPE", short: "H3", kind: "high" },
  H4: { label: "MIC", short: "H4", kind: "high" },
  L1: { label: "BASS", short: "L1", kind: "low" },
  L2: { label: "NOTE", short: "L2", kind: "low" },
  L3: { label: "MIX", short: "L3", kind: "low" },
  L4: { label: "PALM", short: "L4", kind: "low" },
  L5: { label: "NEON", short: "L5", kind: "low" },
  W: { label: "WILD", short: "W", kind: "wild" },
  S: { label: "SUN", short: "S", kind: "scatter" },
};

export function getWinLevel(winAmount, key = "standard") {
  const levels =
    key === "endFeature"
      ? [
          [0, 1, 1],
          [1, 5, 2],
          [5, 10, 3],
          [10, 20, 4],
          [20, 50, 5],
          [50, 100, 6],
          [100, 500, 7],
          [500, 2000, 8],
          [2000, GAME.wincap, 9],
          [GAME.wincap, Infinity, 10],
        ]
      : [
          [0, 0.1, 1],
          [0.1, 1, 2],
          [1, 2, 3],
          [2, 5, 4],
          [5, 15, 5],
          [15, 30, 6],
          [30, 50, 7],
          [50, 100, 8],
          [100, GAME.wincap, 9],
          [GAME.wincap, Infinity, 10],
        ];
  for (const [lo, hi, level] of levels) {
    if (winAmount >= lo && winAmount < hi) return level;
  }
  return 1;
}

export function toCents(amount) {
  return Math.round(Math.min(amount, GAME.wincap) * 100);
}
