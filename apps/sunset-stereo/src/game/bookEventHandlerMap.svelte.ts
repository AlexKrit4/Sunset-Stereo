import { hideSpinWin, showSpinWin, ui } from "../lib/ui.svelte";
import { waitForTimeout } from "../utils/waitForTimeout";
import { runtime } from "./context";
import { formatMoneyPlain, multiplierCentsToMicro } from "../rgs/money";
import type { BookEventHandlerMap, Position, RawSymbol } from "./typesBookEvent";

let lastBoard: RawSymbol[][] = [];
let pendingHolds: Position[] = [];

export const bookEventHandlerMap: BookEventHandlerMap = {
  reveal: async (bookEvent) => {
    hideSpinWin();
    const board = runtime.board;
    if (!board) return;
    lastBoard = bookEvent.board;
    const pace =
      bookEvent.gameType === "basegame" ? "base" : pendingHolds.length ? "respin" : "bonus";
    if (bookEvent.gameType === "basegame") {
      ui.feature = false;
      ui.fsCurrent = 0;
      ui.fsTotal = 0;
      pendingHolds = [];
    }
    await board.playBookReveal(bookEvent.board, {
      pace,
      anticipation: bookEvent.anticipation,
      holds: pendingHolds,
    });
    if (pendingHolds.length) board.applyBookHolds(bookEvent.board, pendingHolds);
  },

  holdRespin: async (bookEvent) => {
    pendingHolds = bookEvent.positions;
    runtime.board?.applyBookHolds(lastBoard, pendingHolds);
    await waitForTimeout(180);
  },

  winInfo: async (bookEvent) => {
    const positions = bookEvent.wins.flatMap((win) => win.positions);
    await runtime.board?.showBookWins(positions);
    await waitForTimeout(120);
  },

  setWin: async (bookEvent) => {
    const micro = multiplierCentsToMicro(bookEvent.amount);
    ui.winMicro = micro;
    showSpinWin(micro);
    await waitForTimeout(micro > 0 ? 720 : 60);
  },

  setTotalWin: async (bookEvent) => {
    ui.winMicro = multiplierCentsToMicro(bookEvent.amount);
  },

  freeSpinTrigger: async (bookEvent) => {
    ui.feature = true;
    ui.fsCurrent = 0;
    ui.fsTotal = bookEvent.totalFs;
    ui.banner = "3 suns — 10 extra plays";
    runtime.board?.showBookScatters(lastBoard);
    await waitForTimeout(720);
    runtime.board?.clearBookVisuals();
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
    ui.banner = `Extra play ${bookEvent.amount + 1} / ${bookEvent.total}`;
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
    ui.banner = bookEvent.amount ? `Paid ${formatMoneyPlain(ui.winMicro)}` : "";
    await waitForTimeout(120);
  },
};
