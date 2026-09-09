import { hideSpinWin, showSpinWin, ui, waitForBonusStart } from "../lib/ui.svelte";
import { waitForTimeout } from "../utils/waitForTimeout";
import { runtime } from "./context";
import { unpadPosition, winningWays } from "../rgs/bookView";
import { multiplierCentsToMicro } from "../rgs/money";
import type { BookEvent, BookEventHandlerMap, Position, RawSymbol } from "./typesBookEvent";

let lastBoard: RawSymbol[][] = [];
let pendingHolds: Position[] = [];
let pendingWinLines = 0;

function nextBonusWinPositions(events: BookEvent[], current: BookEvent): Position[] {
  const start = events.indexOf(current);
  for (let index = (start >= 0 ? start + 1 : 0); index < events.length; index += 1) {
    const event = events[index];
    if (event.type === "holdRespin") return event.positions;
    if (event.type === "winInfo") return event.wins.flatMap((win) => win.positions);
    if (
      event.type === "reveal" ||
      event.type === "updateFreeSpin" ||
      event.type === "freeSpinEnd" ||
      event.type === "finalWin"
    ) {
      return [];
    }
  }
  return [];
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
    const upcomingWins =
      bookEvent.gameType === "freegame" ? nextBonusWinPositions(context.bookEvents, bookEvent) : [];
    await board.playBookReveal(bookEvent.board, {
      pace,
      anticipation: bookEvent.anticipation,
      holds: pendingHolds,
      upcomingWins,
    });
    if (pendingHolds.length && !upcomingWins.length) {
      board.applyBookHolds(bookEvent.board, pendingHolds);
    }
    if (bookEvent.gameType === "freegame" && upcomingWins.length) {
      const already = new Set(
        pendingHolds.map((pos) => {
          const cell = unpadPosition(pos);
          return `${cell.reel}:${cell.row}`;
        }),
      );
      const fresh = upcomingWins.filter((pos) => {
        const cell = unpadPosition(pos);
        return !already.has(`${cell.reel}:${cell.row}`);
      });
      if (fresh.length) await board.flashBonusWins(fresh);
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
