import { FREESPINS, GAME, PAYLINES, PAYTABLE, getWinLevel, toCents } from "./config.js";
import { REELS } from "./reels.js";

function mulberry32(seed) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function pickStop(length, rng) {
  return Math.floor(rng() * length);
}

function wrap(index, length) {
  return ((index % length) + length) % length;
}

function drawBoard(reelset, rng) {
  const strips = REELS[reelset];
  const paddingPositions = [];
  const board = [];
  for (let reel = 0; reel < GAME.reels; reel += 1) {
    const strip = strips[reel];
    const stop = pickStop(strip.length, rng);
    paddingPositions.push(stop);
    const column = [];
    for (let offset = -1; offset <= GAME.rows; offset += 1) {
      const name = strip[wrap(stop + offset, strip.length)];
      column.push({ name, wild: name === "W", scatter: name === "S" });
    }
    board.push(column);
  }
  return { board, paddingPositions };
}

function visibleBoard(board) {
  return board.map((column) => column.slice(1, 1 + GAME.rows));
}

function countScatters(board) {
  const positions = [];
  visibleBoard(board).forEach((column, reel) => {
    column.forEach((symbol, row) => {
      if (symbol.scatter) positions.push({ reel, row });
    });
  });
  return positions;
}

function applyWildMult(board, positions, baseWin, globalMult) {
  let lineMult = 1;
  positions.forEach(({ reel, row }) => {
    const symbol = board[reel][row + 1];
    if (symbol.wild && symbol.multiplier && symbol.multiplier > 1) {
      lineMult += symbol.multiplier;
    }
  });
  if (lineMult > 1) lineMult -= 1;
  const applied = Math.max(1, lineMult) * globalMult;
  return { win: baseWin * applied, applied, lineMult: Math.max(1, lineMult) };
}

function evaluateLines(board, globalMult) {
  const active = visibleBoard(board);
  const wins = [];
  let totalWin = 0;

  Object.entries(PAYLINES).forEach(([lineIndex, rows]) => {
    const first = active[0][rows[0]];
    let wildMatches = first.wild ? 1 : 0;
    let matches = first.wild ? 0 : 1;
    let firstNonWild = first.wild ? null : first;
    let finishedWild = !first.wild;
    const potential = [first];

    for (let reel = 1; reel < rows.length; reel += 1) {
      const symbol = active[reel][rows[reel]];
      if (finishedWild) {
        if (symbol.name === firstNonWild.name || symbol.wild) matches += 1;
        else break;
      } else if (symbol.wild && firstNonWild === null) {
        wildMatches += 1;
      } else if (firstNonWild === null) {
        firstNonWild = symbol;
        matches += 1;
        finishedWild = true;
      } else {
        break;
      }
      potential.push(symbol);
    }

    const wildWin = PAYTABLE.W?.[wildMatches] || 0;
    const baseWin = firstNonWild ? PAYTABLE[firstNonWild.name]?.[wildMatches + matches] || 0 : 0;

    if (wildWin > 0 || baseWin > 0) {
      if (wildWin > baseWin) {
        const positions = Array.from({ length: wildMatches }, (_, reel) => ({
          reel,
          row: rows[reel],
        }));
        const { win, applied, lineMult } = applyWildMult(board, positions, wildWin, globalMult);
        wins.push({
          symbol: potential[0].name,
          kind: wildMatches,
          win,
          positions,
          meta: {
            lineIndex: Number(lineIndex),
            multiplier: applied,
            winWithoutMult: wildWin,
            globalMult,
            lineMultiplier: lineMult,
          },
        });
        totalWin += win;
      } else {
        const kind = matches + wildMatches;
        const positions = Array.from({ length: kind }, (_, reel) => ({
          reel,
          row: rows[reel],
        }));
        const { win, applied, lineMult } = applyWildMult(board, positions, baseWin, globalMult);
        wins.push({
          symbol: firstNonWild.name,
          kind,
          win,
          positions,
          meta: {
            lineIndex: Number(lineIndex),
            multiplier: applied,
            winWithoutMult: baseWin,
            globalMult,
            lineMultiplier: lineMult,
          },
        });
        totalWin += win;
      }
    }
  });

  return { totalWin, wins };
}

function attachWildMults(board, rng, freegame) {
  const weights = [
    [2, 70],
    [3, 75],
    [4, 40],
    [5, 18],
    [8, 12],
    [10, 8],
    [20, 5],
    [50, 2],
  ];
  const total = weights.reduce((sum, [, w]) => sum + w, 0);
  board.forEach((column) => {
    column.forEach((symbol) => {
      if (!symbol.wild) return;
      if (!freegame) {
        symbol.multiplier = 1;
        return;
      }
      let roll = rng() * total;
      for (const [value, weight] of weights) {
        roll -= weight;
        if (roll <= 0) {
          symbol.multiplier = value;
          return;
        }
      }
      symbol.multiplier = 2;
    });
  });
}

function addEvent(events, type, extra) {
  events.push({ index: events.length, type, ...extra });
}

function serializeBoard(board) {
  return board.map((column) =>
    column.map((symbol) => {
      const out = { name: symbol.name };
      if (symbol.wild) out.wild = true;
      if (symbol.scatter) out.scatter = true;
      if (symbol.multiplier) out.multiplier = symbol.multiplier;
      return out;
    }),
  );
}

function padPositions(positions) {
  return positions.map((pos) => ({ reel: pos.reel, row: pos.row + 1 }));
}

function emitWinEvents(events, winData, spinWin, runningWin) {
  if (spinWin > 0) {
    addEvent(events, "winInfo", {
      totalWin: toCents(winData.totalWin),
      wins: winData.wins.map((win) => ({
        ...win,
        win: toCents(win.win),
        positions: padPositions(win.positions),
        meta: {
          ...win.meta,
          winWithoutMult: toCents(win.meta.winWithoutMult),
        },
      })),
    });
    addEvent(events, "setWin", {
      amount: toCents(spinWin),
      winLevel: getWinLevel(spinWin),
    });
  }
  addEvent(events, "setTotalWin", { amount: toCents(runningWin) });
}

function spinOnce(reelset, rng, freegame) {
  const drawn = drawBoard(reelset, rng);
  attachWildMults(drawn.board, rng, freegame);
  return drawn;
}

export function playRound({ seed = Date.now(), buyBonus = false } = {}) {
  const rng = mulberry32(seed);
  const events = [];
  let runningWin = 0;
  let freeGameWins = 0;
  let baseGameWins = 0;
  let globalMult = 1;

  const baseDraw = spinOnce("BR0", rng, false);
  addEvent(events, "reveal", {
    board: serializeBoard(baseDraw.board),
    paddingPositions: baseDraw.paddingPositions,
    gameType: "basegame",
    anticipation: [0, 0, 0, 0, 0],
  });

  const baseWin = evaluateLines(baseDraw.board, 1);
  runningWin += baseWin.totalWin;
  baseGameWins = baseWin.totalWin;
  emitWinEvents(events, baseWin, baseWin.totalWin, runningWin);

  const scatters = countScatters(baseDraw.board);
  const shouldBonus = buyBonus || scatters.length >= 3;
  if (shouldBonus) {
    const scatterCount = buyBonus ? Math.max(3, scatters.length) : scatters.length;
    let totalFs = FREESPINS.basegame[scatterCount] || FREESPINS.basegame[3];
    const triggerPositions =
      scatters.length >= 3
        ? padPositions(scatters)
        : [
            { reel: 0, row: 2 },
            { reel: 2, row: 2 },
            { reel: 4, row: 2 },
          ];
    addEvent(events, "freeSpinTrigger", { totalFs, positions: triggerPositions });
    addEvent(events, "updateGlobalMult", { globalMult: 1 });

    let fs = 0;
    while (fs < totalFs) {
      addEvent(events, "updateFreeSpin", { amount: fs, total: totalFs });
      fs += 1;
      const freeDraw = spinOnce("FR0", rng, true);
      addEvent(events, "reveal", {
        board: serializeBoard(freeDraw.board),
        paddingPositions: freeDraw.paddingPositions,
        gameType: "freegame",
        anticipation: [0, 0, 0, 0, 0],
      });
      const freeWin = evaluateLines(freeDraw.board, globalMult);
      runningWin = Math.min(runningWin + freeWin.totalWin, GAME.wincap);
      freeGameWins += freeWin.totalWin;
      emitWinEvents(events, freeWin, freeWin.totalWin, runningWin);
      if (freeWin.totalWin > 0 && runningWin < GAME.wincap) {
        globalMult += 1;
        addEvent(events, "updateGlobalMult", { globalMult });
      }
      const freeScatters = countScatters(freeDraw.board);
      if (freeScatters.length >= 3) {
        totalFs += FREESPINS.freegame[freeScatters.length] || 0;
        addEvent(events, "freeSpinRetrigger", {
          totalFs,
          positions: padPositions(freeScatters),
        });
      }
    }
    addEvent(events, "freeSpinEnd", {
      amount: toCents(freeGameWins),
      winLevel: getWinLevel(freeGameWins, "endFeature"),
    });
  }

  const finalWin = Math.min(runningWin, GAME.wincap);
  addEvent(events, "finalWin", { amount: toCents(finalWin) });

  return {
    id: seed,
    payoutMultiplier: toCents(finalWin),
    events,
    criteria: shouldBonus ? "freegame" : finalWin > 0 ? "basegame" : "0",
    baseGameWins,
    freeGameWins,
  };
}
