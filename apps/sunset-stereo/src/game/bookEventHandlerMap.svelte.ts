import { eventEmitter } from "./eventEmitter";
import { getContext } from "./context";
import { ui, scaled } from "../lib/ui.svelte";
import { waitForTimeout } from "../utils/waitForTimeout";
import type { BookEventHandlerMap } from "./typesBookEvent";

export const bookEventHandlerMap: BookEventHandlerMap = {
  reveal: async (bookEvent) => {
    const { board } = getContext();
    if (bookEvent.gameType === "basegame") {
      ui.feature = false;
      ui.mix = 1;
      ui.fsCurrent = 0;
      ui.fsTotal = 0;
    }
    await eventEmitter.broadcast({
      type: "revealBoard",
      board: bookEvent.board,
      gameType: bookEvent.gameType,
      anticipation: bookEvent.anticipation,
    });
    await board?.spinTo(bookEvent);
    await eventEmitter.broadcast({ type: "boardLand", gameType: bookEvent.gameType });
  },

  winInfo: async (bookEvent) => {
    const { board } = getContext();
    await board?.showWins(bookEvent.wins);
  },

  setWin: async (bookEvent) => {
    ui.win = scaled(bookEvent.amount);
    await waitForTimeout(80);
  },

  setTotalWin: async (bookEvent) => {
    ui.win = scaled(bookEvent.amount);
  },

  freeSpinTrigger: async (bookEvent) => {
    ui.feature = true;
    ui.fsCurrent = 0;
    ui.fsTotal = bookEvent.totalFs;
    ui.banner = `Golden Hour — ${bookEvent.totalFs} extra plays`;
    const { board } = getContext();
    await eventEmitter.broadcast({ type: "featureStart", total: bookEvent.totalFs });
    await board?.flashScatters(bookEvent.positions);
    await waitForTimeout(280);
  },

  freeSpinRetrigger: async (bookEvent) => {
    ui.fsTotal = bookEvent.totalFs;
    ui.banner = `Retrigger — ${bookEvent.totalFs} extra plays`;
    const { board } = getContext();
    await board?.flashScatters(bookEvent.positions);
    await waitForTimeout(360);
  },

  updateFreeSpin: async (bookEvent) => {
    ui.fsCurrent = bookEvent.amount + 1;
    ui.fsTotal = bookEvent.total;
    ui.banner = `Golden Hour ${bookEvent.amount + 1} / ${bookEvent.total}`;
    await eventEmitter.broadcast({
      type: "fsUpdate",
      current: bookEvent.amount + 1,
      total: bookEvent.total,
    });
    await waitForTimeout(80);
  },

  updateGlobalMult: async (bookEvent) => {
    ui.mix = bookEvent.globalMult;
    ui.banner = `Stereo Mix ×${bookEvent.globalMult}`;
    await eventEmitter.broadcast({ type: "mixUpdate", value: bookEvent.globalMult });
    await waitForTimeout(220);
  },

  freeSpinEnd: async (bookEvent) => {
    ui.banner = bookEvent.amount ? `Golden Hour paid ${scaled(bookEvent.amount).toFixed(2)}` : "Golden Hour ended";
    await eventEmitter.broadcast({ type: "featureEnd", amount: bookEvent.amount });
    await waitForTimeout(320);
    ui.feature = false;
  },

  finalWin: async (bookEvent) => {
    const paid = scaled(bookEvent.amount);
    ui.win = paid;
    if (paid > 0) ui.balance += paid;
    ui.banner = paid ? `Paid ${paid.toFixed(2)}` : "";
    await waitForTimeout(160);
  },
};
