import {
  BETS,
  GAME,
  NUM_REELS,
  PAYABLE,
  PAYOUTS,
  REEL_ROWS,
  SCATTER_REEL_LAND_CHANCE,
  SCATTER_REELS,
  SCATTER_TEASE_ENTER_MS,
  SCATTER_TEASE_SLOW_MS,
  SCATTER_TEASE_STOP_MS,
  SCATTER_TEASE_TOTAL_MS,
  SCATTER_WEIGHT,
  SYMBOLS,
  WAYS_TEASE_INTER_REEL_MS,
  WAYS_TEASE_MIN_REELS,
  XNUDGE_CLUSTER_STRIP_CHANCE,
  XNUDGE_LAND_CHANCE,
  XNUDGE_REELS,
  XNUDGE_STACK_SIZE,
  XWAYS_REDUCTION,
  XWAYS_REELS,
} from "./config.js";

function mulberry32(seed) {
  let t = seed >>> 0;
  return {
    random() {
      t += 0x6d2b79f5;
      let r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    },
    randomInt(min, max) {
      const lo = Math.ceil(min);
      const hi = Math.floor(max);
      if (hi <= lo) return lo;
      return lo + Math.floor(this.random() * (hi - lo + 1));
    },
  };
}

export function cloneGrid(grid) {
  return grid.map((col) => [...col]);
}

export function getReelRows(reel) {
  return REEL_ROWS[reel];
}

export function getXNudgeVisibleCount(symbols) {
  if (!symbols?.length) return 0;
  let n = 0;
  for (let row = 0; row < symbols.length; row += 1) {
    if (symbols[row] !== "xNudge") break;
    n += 1;
  }
  return n;
}

export function cellMatches(sym, cell) {
  return cell === sym || cell === "wild";
}

function getSymbolWeight(name, reelIndex, omitScatter) {
  if (name === "xWays") {
    return reelIndex >= 0 && XWAYS_REELS.includes(reelIndex) ? 1 / XWAYS_REDUCTION : 0;
  }
  if (name === "xNudge" || name === "wild") return 0;
  if (name === "scatter") {
    if (omitScatter) return 0;
    return reelIndex >= 0 && SCATTER_REELS.includes(reelIndex) ? SCATTER_WEIGHT : 0;
  }
  return 1;
}

function pickRandomSymbol(rng, reelIndex, omitScatter = false) {
  const weights = SYMBOLS.map((name) => getSymbolWeight(name, reelIndex, omitScatter));
  const total = weights.reduce((a, b) => a + b, 0);
  let r = rng.random() * total;
  for (let i = 0; i < weights.length; i += 1) {
    r -= weights[i];
    if (r <= 0) return SYMBOLS[i];
  }
  return SYMBOLS[0];
}

function generateReelColumn(rng, reelIndex) {
  const rows = getReelRows(reelIndex);
  const col = Array.from({ length: rows }, () => pickRandomSymbol(rng, reelIndex, true));
  if (SCATTER_REELS.includes(reelIndex) && rng.random() < SCATTER_REEL_LAND_CHANCE) {
    col[rng.randomInt(0, rows - 1)] = "scatter";
  }
  return col;
}

function placeXNudgeStacks(rng, b) {
  const stacks = [];
  for (const reel of XNUDGE_REELS) {
    if (rng.random() > XNUDGE_LAND_CHANCE) continue;
    const rows = getReelRows(reel);
    const visible = rng.randomInt(1, Math.min(XNUDGE_STACK_SIZE, rows));
    for (let row = 0; row < visible; row += 1) b[reel][row] = "xNudge";
    stacks.push({ reel, visible });
  }
  return stacks;
}

function generateRawBoard(rng) {
  const b = REEL_ROWS.map((_, r) => generateReelColumn(rng, r));
  const stacks = placeXNudgeStacks(rng, b);
  return { b, stacks };
}

function resolveXWays(rng, b, m) {
  const replacement = PAYABLE[Math.floor(rng.random() * PAYABLE.length)];
  const positions = [];
  for (let r = 0; r < NUM_REELS; r += 1) {
    for (let row = 0; row < getReelRows(r); row += 1) {
      if (b[r][row] === "xWays") {
        const mult = rng.randomInt(2, 6);
        positions.push({ reel: r, row, replacement, mult });
        b[r][row] = replacement;
        m[r][row] = mult;
      }
    }
  }
  return { positions, replacement };
}

function resolveXNudge(b, m, reelNudgeMult) {
  const steps = [];
  for (const reel of XNUDGE_REELS) {
    let visible = getXNudgeVisibleCount(b[reel]);
    if (visible === 0) continue;
    const rows = getReelRows(reel);
    const target = Math.min(XNUDGE_STACK_SIZE, rows);
    const landVisible = visible;
    let nudges = 0;
    let mult = 1;
    if (visible >= target) {
      mult = target;
    } else {
      nudges = target - visible;
      for (let step = 0; step < nudges; step += 1) {
        mult += 1;
        b[reel][visible] = "xNudge";
        visible += 1;
      }
    }
    reelNudgeMult[reel] = mult;
    for (let row = 0; row < rows; row += 1) {
      b[reel][row] = "wild";
      m[reel][row] = 1;
    }
    steps.push({ reel, landVisible, nudges, mult });
  }
  return steps;
}

function countWaysOnReel(sym, b, m, reel) {
  let count = 0;
  for (let row = 0; row < getReelRows(reel); row += 1) {
    if (cellMatches(sym, b[reel][row])) count += m[reel][row] || 1;
  }
  return count;
}

function calculateWaysWin(bet, b, m, reelNudgeMult) {
  let totalWin = 0;
  let totalWays = 0;
  const wins = [];
  const highlights = [];
  const highlightKeys = new Set();

  for (const sym of PAYABLE) {
    let reelsMatched = 0;
    let ways = 1;
    let nudgeLineMult = 1;
    for (let r = 0; r < NUM_REELS; r += 1) {
      const countOnReel = countWaysOnReel(sym, b, m, r);
      if (countOnReel === 0) break;
      reelsMatched += 1;
      ways *= countOnReel;
      nudgeLineMult *= reelNudgeMult[r] || 1;
    }
    if (reelsMatched < 3) continue;
    const payMult = PAYOUTS[sym][reelsMatched] ?? PAYOUTS[sym][6] ?? 0;
    const win = bet * payMult * ways * nudgeLineMult;
    if (win <= 0) continue;
    wins.push({ sym, reelsMatched, ways, nudgeLineMult, win });
    totalWin += win;
    totalWays += ways;
    for (let r = 0; r < reelsMatched; r += 1) {
      for (let row = 0; row < getReelRows(r); row += 1) {
        if (!cellMatches(sym, b[r][row])) continue;
        const key = `${r}:${row}`;
        if (highlightKeys.has(key)) continue;
        highlightKeys.add(key);
        highlights.push({ reel: r, row });
      }
    }
  }
  const cap = bet * GAME.wincap;
  if (totalWin > cap) totalWin = cap;
  return { totalWin, totalWays, wins, highlights };
}

function reelHasScatter(b, reel) {
  return b[reel].some((cell) => cell === "scatter");
}

function reelHasPayable(b, reel, sym) {
  return b[reel].some((cell) => cellMatches(sym, cell));
}

function reelMatchesWaysTease(b, reel, sym) {
  if (reelHasPayable(b, reel, sym)) return true;
  return XNUDGE_REELS.includes(reel) && getXNudgeVisibleCount(b[reel]) > 0;
}

function getWaysTeaseSymbol(b, upToReelInclusive) {
  const reelsMatched = upToReelInclusive + 1;
  if (reelsMatched < WAYS_TEASE_MIN_REELS) return null;
  let bestSym = null;
  let bestPay = 0;
  for (const sym of PAYABLE) {
    let ok = true;
    for (let r = 0; r <= upToReelInclusive; r += 1) {
      if (!reelMatchesWaysTease(b, r, sym)) {
        ok = false;
        break;
      }
    }
    if (!ok) continue;
    const pay = PAYOUTS[sym][reelsMatched] ?? PAYOUTS[sym][6] ?? 0;
    if (pay > bestPay) {
      bestPay = pay;
      bestSym = sym;
    }
  }
  return bestSym;
}

function buildWaysTeaseGaps(b) {
  const gaps = Array(NUM_REELS).fill(0);
  for (let nextReel = WAYS_TEASE_MIN_REELS; nextReel < NUM_REELS; nextReel += 1) {
    if (getWaysTeaseSymbol(b, nextReel - 1)) gaps[nextReel] += WAYS_TEASE_INTER_REEL_MS;
  }
  return gaps;
}

function twoScatterTeaseMs() {
  return SCATTER_TEASE_ENTER_MS + SCATTER_TEASE_SLOW_MS + SCATTER_TEASE_STOP_MS;
}

function buildScatterTeaseGaps(b) {
  const gaps = Array(NUM_REELS).fill(0);
  const hit = SCATTER_REELS.filter((r) => reelHasScatter(b, r)).sort((a, c) => a - c);
  const addGap = (fromReel, toReel) => {
    const count = Math.max(0, toReel - fromReel + 1);
    if (!count) return;
    let assigned = 0;
    for (let r = fromReel; r <= toReel; r += 1) {
      const isLast = r === toReel;
      const add = isLast ? SCATTER_TEASE_TOTAL_MS - assigned : Math.floor(SCATTER_TEASE_TOTAL_MS / count);
      gaps[r] += add;
      assigned += add;
    }
  };
  if (hit.length >= 3) addGap(hit[1] + 1, hit[hit.length - 1]);
  else if (hit.length === 2) {
    const next = Math.max(...hit) + 1;
    if (next < NUM_REELS) gaps[next] += twoScatterTeaseMs();
  }
  return { gaps, hit };
}

export function pickStripSymbol(rng, reelIndex) {
  return pickRandomSymbol(rng, reelIndex, true);
}

export function pickStripItems(rng, reelIndex, count) {
  const items = [];
  let len = 0;
  const canCluster = XNUDGE_REELS.includes(reelIndex);
  while (len < count) {
    const remaining = count - len;
    if (canCluster && remaining >= XNUDGE_STACK_SIZE && rng.random() < XNUDGE_CLUSTER_STRIP_CHANCE) {
      for (let i = 0; i < XNUDGE_STACK_SIZE; i += 1) items.push("xNudge");
      len += XNUDGE_STACK_SIZE;
      continue;
    }
    items.push(pickRandomSymbol(rng, reelIndex, true));
    len += 1;
  }
  return items;
}

function countScatters(b) {
  let n = 0;
  for (let r = 0; r < NUM_REELS; r += 1) {
    if (reelHasScatter(b, r)) n += 1;
  }
  return n;
}

export function playRound({ seed = Date.now(), bet = 1 } = {}) {
  const rng = mulberry32(seed);
  const { b: raw, stacks } = generateRawBoard(rng);
  const resolved = cloneGrid(raw);
  const mults = resolved.map((col) => col.map(() => 1));
  const reelNudgeMult = Array(NUM_REELS).fill(1);
  const xWays = resolveXWays(rng, resolved, mults);
  const nudge = resolveXNudge(resolved, mults, reelNudgeMult);
  const winInfo = calculateWaysWin(bet, resolved, mults, reelNudgeMult);
  const waysGaps = buildWaysTeaseGaps(raw);
  const scatter = buildScatterTeaseGaps(raw);
  const extraStopMs = waysGaps.map((ms, i) => ms + scatter.gaps[i]);

  return {
    raw,
    resolved,
    mults,
    reelNudgeMult,
    stacks,
    xWays,
    nudge,
    extraStopMs,
    waysGaps,
    scatterGaps: scatter.gaps,
    scatterHit: scatter.hit,
    scatterCount: countScatters(raw),
    bet,
    ...winInfo,
  };
}

export { BETS, getWaysTeaseSymbol, reelMatchesWaysTease, XNUDGE_REELS, XWAYS_REELS, SCATTER_REELS };
