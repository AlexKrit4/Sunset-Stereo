import { hideSpinWin, showSpinWin, ui, waitForBonusStart } from "../lib/ui.svelte";
import { waitForTimeout } from "../utils/waitForTimeout";
import { runtime } from "./context";
import { unpadPosition, winningWays } from "../rgs/bookView";
import { multiplierCentsToMicro } from "../rgs/money";
import type { BookEvent, BookEventHandlerMap, Position, RawSymbol } from "./typesBookEvent";

let lastBoard: RawSymbol[][] = [];
let pendingHolds: Position[] = [];
let pendingWinLines = 0;

function cellKey(pos: Position) {
  const cell = unpadPosition(pos);
  return `${cell.reel}:${cell.row}`;
}

function nextBonusWin(
  events: BookEvent[],
  current: BookEvent,
): { positions: Position[]; beforeRespin: boolean } | null {
  let start = events.indexOf(current);
  if (start < 0) start = events.findIndex((event) => event.index === current.index);
  if (start < 0) return null;
  for (let index = start + 1; index < events.length; index += 1) {
    const event = events[index];
    if (event.type === "holdRespin") return { positions: event.positions, beforeRespin: true };
    if (event.type === "winInfo") return { positions: event.wins.flatMap((win) => win.positions), beforeRespin: false };
    if (
      event.type === "reveal" ||
      event.type === "updateFreeSpin" ||
      event.type === "freeSpinEnd" ||
      event.type === "finalWin"
    ) {
      return null;
    }
  }
  return null;
}

export const bookEventHandlerMap: BookEventHandlerMap = {
  reveal: async (bookEvent, context) => {
    hideSpinWin();
    pendingWinLines = 0;
    const board = runtime.board;
    if (!board) return;
    lastBoard = bookEvent.board;
    const pace = bookEvent.gameType === "basegame" ? "base" : "bonus";
    if (bookEvent.gameType === "basegame") {
      ui.feature = false;
      ui.fsCurrent = 0;
      ui.fsTotal = 0;
      pendingHolds = [];
      board.clearBookVisuals();
    }
    const upcoming = bookEvent.gameType === "freegame" ? nextBonusWin(context.bookEvents, bookEvent) : null;
    await board.playBookReveal(bookEvent.board, {
      pace,
      anticipation: bookEvent.anticipation,
      holds: pendingHolds,
    });
    if (pendingHolds.length && !upcoming?.beforeRespin) {
      board.applyBookHolds(bookEvent.board, pendingHolds);
    }
    if (upcoming?.beforeRespin) {
      const already = new Set(pendingHolds.map(cellKey));
      const fresh = upcoming.positions.filter((pos) => !already.has(cellKey(pos)));
      await board.presentNewBonusWins(fresh, upcoming.positions, pendingHolds.length === 0);
    }
  },

  holdRespin: async (bookEvent) => {
    pendingHolds = bookEvent.positions;
    runtime.board?.lockBonusWinners(bookEvent.positions);
    await waitForTimeout(80);
  },

  winInfo: async (bookEvent) => {
    pendingWinLines = winningWays(bookEvent.wins);
    const positions = bookEvent.wins.flatMap((win) => win.positions);
    await runtime.board?.showBookWins(positions);
    await waitForTimeout(120);
  },

  setWin: async (bookEvent) => {
    const micro = multiplierCentsToMicro(bookEvent.amount);
    ui.winMicro = micro;
    if (micro <= 0) {
      hideSpinWin();
      await waitForTimeout(60);
      return;
    }
    await waitForTimeout(640);
    showSpinWin(micro, pendingWinLines);
    await waitForTimeout(1100);
  },

  setTotalWin: async (bookEvent) => {
    ui.winMicro = multiplierCentsToMicro(bookEvent.amount);
  },

  freeSpinTrigger: async (bookEvent) => {
    ui.feature = true;
    ui.fsCurrent = 0;
    ui.fsTotal = bookEvent.totalFs;
    ui.banner = "";
    runtime.board?.clearBookVisuals();
    await waitForBonusStart(bookEvent.totalFs);
  },

  freeSpinRetrigger: async (bookEvent) => {
    ui.fsTotal = bookEvent.totalFs;
    ui.banner = `Retrigger — ${bookEvent.totalFs} extra plays`;
    await waitForTimeout(280);
  },

  updateFreeSpin: async (bookEvent) => {
    hideSpinWin();
    pendingHolds = [];
    runtime.board?.clearBookVisuals();
    ui.fsCurrent = bookEvent.amount + 1;
    ui.fsTotal = bookEvent.total;
    ui.banner = "";
    await waitForTimeout(40);
  },

  updateGlobalMult: async (bookEvent) => {
    ui.mix = bookEvent.globalMult;
  },

  wincap: async () => {
    ui.banner = "Max win";
    await waitForTimeout(400);
  },

  freeSpinEnd: async () => {
    pendingHolds = [];
    runtime.board?.clearBookVisuals();
    ui.feature = false;
    ui.fsCurrent = 0;
    ui.fsTotal = 0;
    await waitForTimeout(200);
  },

  finalWin: async (bookEvent) => {
    ui.winMicro = multiplierCentsToMicro(bookEvent.amount);
    ui.banner = "";
    await waitForTimeout(120);
  },
};
