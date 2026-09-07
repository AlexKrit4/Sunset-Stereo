import { GAME } from "./config.js";
import { createEventEmitter, createPlayBookUtils, wait } from "./events.js";
import { playRound } from "./math.js";
import {
  buildBoard,
  changeBet,
  chargeBet,
  enterGoldenHour,
  exitGoldenHour,
  getState,
  markScatters,
  revealBoard,
  setBalanceDelta,
  setBusy,
  setStereoMix,
  setWinAmount,
  showWins,
  updateFreeSpins,
  renderHud,
} from "./ui.js";

const emitter = createEventEmitter();

const bookEventHandlerMap = {
  reveal: async (bookEvent) => {
    emitter.broadcast({ type: "boardSpin" });
    await revealBoard(bookEvent);
    emitter.broadcast({ type: "boardLand", gameType: bookEvent.gameType });
  },
  winInfo: async (bookEvent) => {
    await showWins(bookEvent);
  },
  setWin: async (bookEvent) => {
    setWinAmount(scaled(bookEvent.amount));
  },
  setTotalWin: async (bookEvent) => {
    setWinAmount(scaled(bookEvent.amount));
  },
  freeSpinTrigger: async (bookEvent) => {
    markScatters(bookEvent.positions || []);
    await enterGoldenHour(bookEvent.totalFs);
  },
  freeSpinRetrigger: async (bookEvent) => {
    markScatters(bookEvent.positions || []);
    updateFreeSpins(getState().freeSpin.current, bookEvent.totalFs);
    await wait(500);
  },
  updateFreeSpin: async (bookEvent) => {
    updateFreeSpins(bookEvent.amount + 1, bookEvent.total);
  },
  updateGlobalMult: async (bookEvent) => {
    setStereoMix(bookEvent.globalMult);
    await wait(180);
  },
  freeSpinEnd: async (bookEvent) => {
    await exitGoldenHour(scaled(bookEvent.amount));
  },
  finalWin: async (bookEvent) => {
    setWinAmount(scaled(bookEvent.amount));
    if (bookEvent.amount > 0) setBalanceDelta(scaled(bookEvent.amount));
  },
};

function scaled(cents) {
  return Math.round(cents * getState().bet);
}

const { playBookEvents } = createPlayBookUtils(bookEventHandlerMap, emitter);

async function run(buyBonus = false) {
  if (getState().busy) return;
  const costMult = buyBonus ? GAME.buyBonusCost : 1;
  if (!chargeBet(costMult)) {
    document.getElementById("toast").textContent = "Not enough balance";
    document.getElementById("toast").classList.add("show");
    setTimeout(() => document.getElementById("toast").classList.remove("show"), 900);
    return;
  }
  setBusy(true);
  const book = playRound({ seed: Date.now() ^ Math.floor(Math.random() * 1e9), buyBonus });
  await playBookEvents(book.events);
  setBusy(false);
}

function bind() {
  document.getElementById("spinBtn").addEventListener("click", () => run(false));
  document.getElementById("bonusBtn").addEventListener("click", () => run(true));
  document.getElementById("betDown").addEventListener("click", () => changeBet(-1));
  document.getElementById("betUp").addEventListener("click", () => changeBet(1));
  document.addEventListener("keydown", (event) => {
    if (event.code === "Space") {
      event.preventDefault();
      run(false);
    }
  });
}

buildBoard();
renderHud();
bind();
