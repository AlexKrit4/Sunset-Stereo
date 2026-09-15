import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mulberry32, playHoldRespinSpin } from "../src/math/math.js";
import { BONUS_SPINS } from "../src/math/config.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const booksPath = join(root, "src/rgs/demoBooks.json");
const data = JSON.parse(readFileSync(booksPath, "utf8"));

const FROM_MATH = {
  H1: "high1",
  H2: "high2",
  H3: "high3",
  H4: "high4",
  H5: "high5",
  L1: "low1",
  L2: "low2",
  L3: "low3",
  L4: "low4",
  L5: "low5",
  W: "wild",
  S: "scatter",
};
const TO_MATH = Object.fromEntries(Object.entries(FROM_MATH).map(([math, name]) => [name, math]));
const SCATTER_REELS = [1, 2, 3, 4];
const VISIBLE_ROWS = [1, 2, 3, 4];
const PAD = ["L5", "L4", "L3", "L2", "L1", "H5"];

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function scatterPositions(board) {
  const found = [];
  board.forEach((col, reel) => {
    col.forEach((cell, row) => {
      if (cell?.name === "S" || cell?.scatter) found.push({ reel, row });
    });
  });
  return found;
}

function addFourthScatter(board, trigger, rng) {
  const present = new Set(
    scatterPositions(board)
      .filter((pos) => VISIBLE_ROWS.includes(pos.row))
      .map((pos) => pos.reel),
  );
  const missing = SCATTER_REELS.filter((reel) => !present.has(reel));
  if (!missing.length) return;
  const reel = missing[0];
  const row = VISIBLE_ROWS[rng.randomInt(0, VISIBLE_ROWS.length - 1)];
  board[reel][row] = { name: "S", scatter: true };
  const positions = [...(trigger.positions ?? [])];
  if (!positions.some((pos) => pos.reel === reel && pos.row === row)) positions.push({ reel, row });
  trigger.positions = positions;
}

function toBookCell(name) {
  if (name === "wild") return { name: "W", wild: true };
  if (name === "scatter") return { name: "S", scatter: true };
  return { name: TO_MATH[name] ?? name };
}

function padBoard(visible) {
  return visible.map((col, reel) => [toBookCell(PAD[reel]), ...col.map(toBookCell), toBookCell(PAD[(reel + 3) % PAD.length])]);
}

function padPos(pos) {
  return { reel: pos.reel, row: pos.row + 1 };
}

function cents(value) {
  return Math.round(value * 100);
}

function eventsFromSpin(spin) {
  const out = [];
  spin.steps.forEach((step, index) => {
    out.push({
      type: "reveal",
      board: padBoard(step.board),
      paddingPositions: [0, 0, 0, 0, 0, 0],
      gameType: "freegame",
      anticipation: [0, 0, 0, 0, 0, 0],
    });
    const last = index === spin.steps.length - 1;
    if (!last) {
      out.push({
        type: "holdRespin",
        positions: step.locked.map(padPos),
        continuing: true,
      });
      return;
    }
    if (spin.paidWin > 0) {
      out.push({
        type: "winInfo",
        totalWin: cents(spin.paidWin),
        wins: spin.wins.map((win) => ({
          symbol: TO_MATH[win.sym] ?? win.sym,
          kind: win.reelsMatched,
          win: cents(win.win),
          positions: (win.positions ?? []).map(padPos),
          meta: {
            ways: win.ways,
            globalMult: 1,
            winWithoutMult: cents(win.win),
            symbolMult: 0,
          },
        })),
      });
      out.push({ type: "setWin", amount: cents(spin.paidWin), winLevel: 5 });
    }
  });
  return out;
}

function reindex(events) {
  events.forEach((event, index) => {
    event.index = index;
  });
}

function buildWildBook(source, id) {
  const book = clone(source);
  book.id = id;
  book.criteria = "wildbonus";
  const rng = mulberry32(id);
  const sourceEvents = book.events;
  addFourthScatter(sourceEvents[0].board, sourceEvents.find((event) => event.type === "freeSpinTrigger"), rng);

  const head = [];
  for (const event of sourceEvents) {
    if (event.type === "updateFreeSpin") break;
    head.push(event);
  }

  const extra = [];
  let total = head.findLast?.((event) => event.type === "setTotalWin")?.amount ?? 0;
  if (!head.findLast) {
    const lastTotal = [...head].reverse().find((event) => event.type === "setTotalWin");
    total = lastTotal?.amount ?? 0;
  }
  for (let spinIndex = 0; spinIndex < BONUS_SPINS; spinIndex += 1) {
    extra.push({ type: "updateFreeSpin", amount: spinIndex, total: BONUS_SPINS });
    const wild = { reel: rng.randomInt(0, 5), row: rng.randomInt(0, 3) };
    extra.push({ type: "placeWild", reel: wild.reel, row: wild.row + 1 });
    const spin = playHoldRespinSpin(rng, 1, [wild]);
    extra.push(...eventsFromSpin(spin));
    total += cents(spin.paidWin);
    extra.push({ type: "setTotalWin", amount: total });
  }

  const tail = [
    { type: "freeSpinEnd", amount: total, winLevel: 5 },
    { type: "finalWin", amount: total },
  ];
  const events = [...head, ...extra, ...tail];
  reindex(events);
  book.events = events;
  book.payoutMultiplier = total;
  return book;
}

const wildBooks = [];
while (wildBooks.length < 20) {
  const src = data.bonusBooks[wildBooks.length % data.bonusBooks.length];
  wildBooks.push(buildWildBook(src, 92001 + wildBooks.length));
}

data.wildBonusBooks = wildBooks;
writeFileSync(booksPath, JSON.stringify(data));

function extraPlayStats(book) {
  const stats = { extraPlays: 0, winningPlays: 0, winningWithRespin: 0, winningWithoutRespin: 0, wildInWin: 0 };
  let i = 0;
  while (i < book.events.length) {
    if (book.events[i].type !== "placeWild") {
      i += 1;
      continue;
    }
    stats.extraPlays += 1;
    const wild = book.events[i];
    const slice = [];
    i += 1;
    while (i < book.events.length && book.events[i].type !== "placeWild" && book.events[i].type !== "freeSpinEnd") {
      slice.push(book.events[i]);
      i += 1;
    }
    const hasWin = slice.some((event) => event.type === "winInfo");
    const hasRespin = slice.some((event) => event.type === "holdRespin");
    if (hasWin) {
      stats.winningPlays += 1;
      if (hasRespin) stats.winningWithRespin += 1;
      else stats.winningWithoutRespin += 1;
      const win = slice.find((event) => event.type === "winInfo");
      if (
        win.wins.some((item) =>
          item.positions.some((pos) => pos.reel === wild.reel && pos.row === wild.row),
        )
      ) {
        stats.wildInWin += 1;
      }
    }
  }
  return stats;
}

const sample = extraPlayStats(wildBooks[0]);
const all = wildBooks.reduce(
  (acc, book) => {
    const next = extraPlayStats(book);
    acc.winningPlays += next.winningPlays;
    acc.winningWithRespin += next.winningWithRespin;
    acc.winningWithoutRespin += next.winningWithoutRespin;
    acc.wildInWin += next.wildInWin;
    return acc;
  },
  { winningPlays: 0, winningWithRespin: 0, winningWithoutRespin: 0, wildInWin: 0 },
);

process.stdout.write(
  JSON.stringify(
    {
      count: wildBooks.length,
      payout0: wildBooks[0].payoutMultiplier,
      sample,
      all,
    },
    null,
    2,
  ) + "\n",
);
