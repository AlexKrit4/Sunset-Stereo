import { hideSpinWin, roundWinBeatsStake, showSpinWin, ui, waitForBonusStart } from "../lib/ui.svelte";
import { beginBigWinIntro, isBigWin, playBigWin } from "../lib/bigWin";
import { bigWinHudBase, followingWincap, wincapStageWin } from "../lib/bigWinStages.js";
import { waitForTimeout } from "../utils/waitForTimeout";
import { paceMs } from "../lib/pace";
import { runtime } from "./context";
import { unpadPosition, winningWays } from "../rgs/bookView";
import { multiplierCentsToMicro } from "../rgs/money";
import type { BookEvent, BookEventHandlerMap, Position, RawSymbol } from "./typesBookEvent";

let lastBoard: RawSymbol[][] = [];
let pendingHolds: Position[] = [];
let lockedWilds: Position[] = [];
let pendingWinLines = 0;
let lastSpinWinMicro = 0;

function cellKey(pos: Position) {
  const cell = unpadPosition(pos);
  return `${cell.reel}:${cell.row}`;
}

function withLockedWilds(positions: Position[]) {
  if (!lockedWilds.length) return positions;
  const seen = new Set(positions.map(cellKey));
  const extra = lockedWilds.filter((pos) => !seen.has(cellKey(pos)));
  return extra.length ? [...positions, ...extra] : positions;
}

function clearLockedWilds() {
  lockedWilds = [];
}

function upcomingTotalWinCents(events: BookEvent[], current: BookEvent) {
  let start = events.indexOf(current);
  if (start < 0) start = events.findIndex((event) => event.index === current.index);
  if (start < 0) return null;
  for (let index = start + 1; index < events.length; index += 1) {
    const event = events[index];
    if (event.type === "setTotalWin") return event.amount;
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
      event.type === "setTotalWin" ||
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
      lastSpinWinMicro = 0;
      clearLockedWilds();
      board.clearBookVisuals({ keepFeature: true });
    }
    const upcoming = bookEvent.gameType === "freegame" ? nextBonusWin(context.bookEvents, bookEvent) : null;
    const holdCells = withLockedWilds(pendingHolds);
    const upcomingPositions = upcoming ? withLockedWilds(upcoming.positions) : [];
    const already = new Set(holdCells.map(cellKey));
    const fresh = upcomingPositions.filter((pos) => !already.has(cellKey(pos)));
    await board.playBookReveal(bookEvent.board, {
      pace,
      anticipation: bookEvent.anticipation,
      holds: holdCells,
      upcomingWins: fresh,
    });
    if (bookEvent.gameType === "basegame") {
      await board.playArmedBaseFeature();
      if (ui.banner === "Stereo Reels" || ui.banner === "Wild Drop") ui.banner = "";
    }
    if (holdCells.length && !upcoming?.beforeRespin) {
      board.applyBookHolds(bookEvent.board, holdCells);
    }
    if (upcoming?.beforeRespin) {
      const firstCombo =
        pendingHolds.length === 0 ||
        (lockedWilds.length > 0 &&
          pendingHolds.every((pos) => lockedWilds.some((wild) => cellKey(wild) === cellKey(pos))));
      await board.presentNewBonusWins(fresh, upcomingPositions, firstCombo);
    }
  },

  holdRespin: async (bookEvent) => {
    pendingHolds = withLockedWilds(bookEvent.positions);
    runtime.board?.lockBonusWinners(pendingHolds);
    await waitForTimeout(paceMs(80));
  },

  placeWild: async (bookEvent) => {
    const board = runtime.board;
    if (!board) return;
    lockedWilds = [{ reel: bookEvent.reel, row: bookEvent.row }];
    pendingHolds = withLockedWilds([]);
    await board.placeWildFromCamera({ reel: bookEvent.reel, row: bookEvent.row });
  },

  baseFeature: async (bookEvent) => {
    const board = runtime.board;
    if (!board) return;
    if (bookEvent.kind === "syncReels" && bookEvent.reels?.length === 2) {
      ui.banner = "Stereo Reels";
      board.armSyncReels(bookEvent.reels[0], bookEvent.reels[1]);
      await waitForTimeout(paceMs(280));
      return;
    }
    if (bookEvent.kind === "placeWilds" && bookEvent.positions?.length) {
      ui.banner = bookEvent.positions.length > 1 ? "Wild Drop" : "Wild Drop";
      board.armBaseWilds(bookEvent.positions);
      await waitForTimeout(paceMs(220));
    }
  },

  winInfo: async (bookEvent, context) => {
    pendingWinLines = winningWays(bookEvent.wins);
    const positions = bookEvent.wins.flatMap((win) => win.positions);
    const sheenWin = multiplierCentsToMicro(bookEvent.totalWin);
    lastSpinWinMicro = sheenWin;
    if (isBigWin(sheenWin, ui.betMicro) || followingWincap(context.bookEvents, bookEvent)) {
      beginBigWinIntro();
    }
    await runtime.board?.showBookWins(positions);
    await waitForTimeout(paceMs(120));
  },

  setWin: async (bookEvent, context) => {
    const micro = multiplierCentsToMicro(bookEvent.amount);
    const totalCents = upcomingTotalWinCents(context.bookEvents, bookEvent);
    const roundWin = totalCents != null ? multiplierCentsToMicro(totalCents) : micro;
    const cap = followingWincap(context.bookEvents, bookEvent);
    if (cap) {
      return;
    }
    if (micro <= 0) {
      ui.winMicro = roundWin;
      hideSpinWin();
      await waitForTimeout(paceMs(60));
      return;
    }
    if (isBigWin(micro, ui.betMicro)) {
      const hudBase = bigWinHudBase(micro, roundWin, ui.winMicro);
      await playBigWin(micro, hudBase);
      ui.winMicro = roundWin;
      return;
    }
    ui.winMicro = roundWin;
    if (ui.feature) {
      await waitForTimeout(paceMs(60));
      return;
    }
    if (!roundWinBeatsStake(roundWin)) {
      await waitForTimeout(paceMs(500));
      return;
    }
    await waitForTimeout(paceMs(640));
    showSpinWin(roundWin, pendingWinLines);
    await waitForTimeout(paceMs(1100));
  },

  setTotalWin: async (bookEvent) => {
    if (ui.bigWinIntro || ui.bigWinOpen) return;
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
    await waitForTimeout(paceMs(280));
  },

  updateFreeSpin: async (bookEvent) => {
    hideSpinWin();
    pendingHolds = [];
    clearLockedWilds();
    runtime.board?.clearBookVisuals();
    ui.fsCurrent = bookEvent.amount + 1;
    ui.fsTotal = bookEvent.total;
    ui.banner = "";
    await waitForTimeout(paceMs(40));
  },

  updateGlobalMult: async (bookEvent) => {
    ui.mix = bookEvent.globalMult;
  },

  wincap: async (bookEvent) => {
    const total = multiplierCentsToMicro(bookEvent.amount);
    const spin = wincapStageWin(total, lastSpinWinMicro, ui.winMicro);
    const paid = bigWinHudBase(spin, total, ui.winMicro);
    if (isBigWin(spin, ui.betMicro) || isBigWin(total, ui.betMicro) || ui.bigWinIntro) {
      await playBigWin(spin, paid);
    }
    ui.winMicro = total;
    ui.banner = "Max win";
    await waitForTimeout(paceMs(1800));
  },

  freeSpinEnd: async (bookEvent) => {
    pendingHolds = [];
    clearLockedWilds();
    runtime.board?.clearBookVisuals();
    const total = multiplierCentsToMicro(bookEvent.amount);
    ui.winMicro = total;
    ui.feature = false;
    ui.wildBonus = false;
    ui.fsCurrent = 0;
    ui.fsTotal = 0;
    if (roundWinBeatsStake(total) && !isBigWin(total, ui.betMicro)) {
      showSpinWin(total, pendingWinLines);
      await waitForTimeout(paceMs(1100));
    } else {
      await waitForTimeout(paceMs(200));
    }
  },

  finalWin: async (bookEvent) => {
    ui.winMicro = multiplierCentsToMicro(bookEvent.amount);
    if (ui.banner !== "Max win") ui.banner = "";
    await waitForTimeout(paceMs(120));
  },
};
