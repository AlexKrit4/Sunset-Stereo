import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { calculateWaysWin } from "../src/math/math.js";

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

function mulberry(seed) {
  let t = seed >>> 0;
  return {
    random() {
      t += 0x6d2b79f5;
      let r = Math.imul(t ^ (t >>> 15), 1 | t);
      r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    },
    int(min, max) {
      return min + Math.floor(this.random() * (max - min + 1));
    },
  };
}

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
  const present = new Set(scatterPositions(board).filter((pos) => VISIBLE_ROWS.includes(pos.row)).map((pos) => pos.reel));
  const missing = SCATTER_REELS.filter((reel) => !present.has(reel));
  if (!missing.length) return;
  const reel = missing[0];
  const row = VISIBLE_ROWS[rng.int(0, VISIBLE_ROWS.length - 1)];
  board[reel][row] = { name: "S", scatter: true };
  const positions = [...(trigger.positions ?? [])];
  if (!positions.some((pos) => pos.reel === reel && pos.row === row)) {
    positions.push({ reel, row });
  }
  trigger.positions = positions;
}

function stampWild(board, reel, row) {
  board[reel][row] = { name: "W", wild: true };
}

function visibleBoard(board) {
  return board.map((col) => col.slice(1, 5).map((cell) => FROM_MATH[cell.name] ?? cell.name));
}

function padPos(pos) {
  return { reel: pos.reel, row: pos.row + 1 };
}

function samePos(a, b) {
  return a.reel === b.reel && a.row === b.row;
}

function unionPositions(list, extra) {
  const out = [...list];
  for (const pos of extra) {
    if (!out.some((item) => samePos(item, pos))) out.push(pos);
  }
  return out;
}

function evaluateBoard(board) {
  const visible = visibleBoard(board);
  const mults = visible.map((col) => col.map(() => 1));
  const info = calculateWaysWin(1, visible, mults, Array(6).fill(1));
  const cents = Math.round(info.totalWin * 100);
  return {
    cents,
    wins: info.wins.map((win) => ({
      symbol: TO_MATH[win.sym] ?? win.sym,
      kind: win.reelsMatched,
      win: Math.round(win.win * 100),
      positions: (win.positions ?? []).map(padPos),
      meta: {
        ways: win.ways,
        globalMult: 1,
        winWithoutMult: Math.round(win.win * 100),
        symbolMult: 0,
      },
    })),
  };
}

function lastReveal(slice) {
  for (let index = slice.length - 1; index >= 0; index -= 1) {
    if (slice[index].type === "reveal") return slice[index];
  }
  return null;
}

function applyWinToSlice(slice, evaluated) {
  const winInfo = slice.find((event) => event.type === "winInfo");
  const setWin = slice.find((event) => event.type === "setWin");
  const oldCents = setWin?.amount ?? winInfo?.totalWin ?? 0;
  if (evaluated.cents <= 0) return 0;
  if (winInfo) {
    winInfo.totalWin = evaluated.cents;
    winInfo.wins = evaluated.wins;
  } else {
    const revealAt = slice.findIndex((event) => event.type === "reveal");
    const insertAt = revealAt >= 0 ? revealAt + 1 : 0;
    slice.splice(insertAt, 0, {
      type: "winInfo",
      totalWin: evaluated.cents,
      wins: evaluated.wins,
    });
  }
  const nextSetWin = slice.find((event) => event.type === "setWin");
  if (nextSetWin) {
    nextSetWin.amount = evaluated.cents;
  } else {
    const infoAt = slice.findIndex((event) => event.type === "winInfo");
    slice.splice(infoAt + 1, 0, { type: "setWin", amount: evaluated.cents, winLevel: 5 });
  }
  return evaluated.cents - oldCents;
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
  const rng = mulberry(id);
  const events = book.events;
  addFourthScatter(events[0].board, events.find((event) => event.type === "freeSpinTrigger"), rng);

  const next = [];
  let index = 0;
  while (index < events.length) {
    const event = events[index];
    if (event.type !== "updateFreeSpin") {
      next.push(event);
      index += 1;
      continue;
    }
    next.push(event);
    const slice = [];
    let cursor = index + 1;
    while (cursor < events.length && events[cursor].type !== "updateFreeSpin" && events[cursor].type !== "freeSpinEnd") {
      slice.push(events[cursor]);
      cursor += 1;
    }
    const reel = rng.int(0, 5);
    const row = VISIBLE_ROWS[rng.int(0, VISIBLE_ROWS.length - 1)];
    const wildPos = { reel, row };
    next.push({ type: "placeWild", reel, row });
    for (const item of slice) {
      if (item.type === "reveal") stampWild(item.board, reel, row);
      if (item.type === "holdRespin") item.positions = unionPositions(item.positions ?? [], [wildPos]);
    }
    const paidBoard = lastReveal(slice);
    const delta = paidBoard ? applyWinToSlice(slice, evaluateBoard(paidBoard.board)) : 0;
    if (delta) {
      for (const item of slice) {
        if (item.type === "setTotalWin") item.amount += delta;
      }
      for (let later = cursor; later < events.length; later += 1) {
        if (events[later].type === "setTotalWin" || events[later].type === "finalWin") {
          events[later].amount += delta;
        }
      }
      book.payoutMultiplier += delta;
    }
    next.push(...slice);
    index = cursor;
  }
  reindex(next);
  book.events = next;
  const finalWin = [...next].reverse().find((event) => event.type === "finalWin");
  if (finalWin) book.payoutMultiplier = finalWin.amount;
  return book;
}

const wildBooks = data.bonusBooks.map((book, index) => buildWildBook(book, 92001 + index));
while (wildBooks.length < 20) {
  const src = data.bonusBooks[wildBooks.length % data.bonusBooks.length];
  wildBooks.push(buildWildBook(src, 92001 + wildBooks.length));
}

data.wildBonusBooks = wildBooks;
writeFileSync(booksPath, JSON.stringify(data));

const sample = wildBooks[0];
const types = sample.events.map((event) => event.type);
const wilds = sample.events.filter((event) => event.type === "placeWild");
const firstWild = wilds[0];
const held = sample.events.filter((event) => event.type === "holdRespin");
const missingHold = held.filter((event) => !event.positions.some((pos) => pos.reel === firstWild.reel && pos.row === firstWild.row));
process.stdout.write(
  JSON.stringify(
    {
      count: wildBooks.length,
      placeWild: types.filter((type) => type === "placeWild").length,
      payout: sample.payoutMultiplier,
      firstWild,
      holdRespinsKeepWild: held.length - missingHold.length,
      holdRespins: held.length,
      winHasWild: sample.events.some(
        (event) =>
          event.type === "winInfo" &&
          event.wins.some((win) => win.positions.some((pos) => pos.reel === firstWild.reel && pos.row === firstWild.row)),
      ),
    },
    null,
    2,
  ) + "\n",
);
