import { BETS, GAME, SYMBOLS } from "./config.js";
import { wait } from "./events.js";

const state = {
  balance: 1000,
  bet: 1,
  win: 0,
  busy: false,
  goldenHour: false,
  stereoMix: 1,
  freeSpin: { current: 0, total: 0 },
};

function el(id) {
  return document.getElementById(id);
}

function formatMoney(value) {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function getState() {
  return state;
}

export function setBusy(busy) {
  state.busy = busy;
  el("spinBtn").disabled = busy;
  el("bonusBtn").disabled = busy;
  el("betDown").disabled = busy;
  el("betUp").disabled = busy;
}

export function renderHud() {
  el("balanceValue").textContent = formatMoney(state.balance);
  el("betValue").textContent = formatMoney(state.bet);
  el("winValue").textContent = formatMoney(state.win);
  el("mixValue").textContent = `${state.stereoMix}×`;
  el("bonusCost").textContent = `${GAME.buyBonusCost}×`;
  const meter = el("mixFill");
  meter.style.width = `${Math.min(100, state.stereoMix * 8)}%`;
}

export function changeBet(delta) {
  const index = BETS.indexOf(state.bet);
  const next = BETS[Math.max(0, Math.min(BETS.length - 1, index + delta))];
  state.bet = next;
  renderHud();
}

function symbolNode(symbol) {
  const meta = SYMBOLS[symbol.name] || { label: symbol.name, short: symbol.name, kind: "low" };
  const tile = document.createElement("div");
  tile.className = `symbol symbol-${symbol.name} kind-${meta.kind}`;
  tile.dataset.name = symbol.name;
  tile.innerHTML = `
    <span class="symbol-glyph" aria-hidden="true"></span>
    <span class="symbol-short">${meta.short}</span>
    <span class="symbol-label">${meta.label}</span>
    ${symbol.multiplier && symbol.multiplier > 1 ? `<span class="symbol-mult">${symbol.multiplier}×</span>` : ""}
  `;
  return tile;
}

export function buildBoard() {
  const board = el("board");
  board.innerHTML = "";
  for (let reel = 0; reel < GAME.reels; reel += 1) {
    const reelEl = document.createElement("div");
    reelEl.className = "reel";
    reelEl.dataset.reel = String(reel);
    const windowEl = document.createElement("div");
    windowEl.className = "reel-window";
    for (let row = 0; row < GAME.rows; row += 1) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.reel = String(reel);
      cell.dataset.row = String(row);
      cell.append(symbolNode({ name: "L5" }));
      windowEl.append(cell);
    }
    reelEl.append(windowEl);
    board.append(reelEl);
  }
}

function setCell(reel, row, symbol) {
  const cell = document.querySelector(`.cell[data-reel="${reel}"][data-row="${row}"]`);
  if (!cell) return;
  cell.replaceChildren(symbolNode(symbol));
}

export async function revealBoard(bookEvent) {
  document.querySelectorAll(".cell").forEach((cell) => cell.classList.remove("win", "scatter"));
  const reels = [...document.querySelectorAll(".reel")];
  reels.forEach((reel) => reel.classList.add("spinning"));
  await wait(state.goldenHour ? 420 : 620);
  for (let reel = 0; reel < GAME.reels; reel += 1) {
    const column = bookEvent.board[reel];
    for (let row = 0; row < GAME.rows; row += 1) {
      setCell(reel, row, column[row + 1]);
    }
    reels[reel].classList.remove("spinning");
    reels[reel].classList.add("landed");
    await wait(90);
    reels[reel].classList.remove("landed");
  }
}

export async function showWins(bookEvent) {
  if (!bookEvent.wins?.length) return;
  bookEvent.wins.forEach((win) => {
    win.positions.forEach((pos) => {
      const cell = document.querySelector(`.cell[data-reel="${pos.reel}"][data-row="${pos.row - 1}"]`);
      if (cell) cell.classList.add("win");
    });
  });
  el("toast").textContent = `${bookEvent.wins.length} line${bookEvent.wins.length === 1 ? "" : "s"}`;
  el("toast").classList.add("show");
  await wait(720);
  el("toast").classList.remove("show");
}

export function setWinAmount(cents) {
  state.win = cents / 100;
  renderHud();
  el("winMeter").classList.add("pulse");
  setTimeout(() => el("winMeter").classList.remove("pulse"), 400);
}

export function setBalanceDelta(cents) {
  state.balance += cents / 100;
  renderHud();
}

export async function enterGoldenHour(totalFs) {
  state.goldenHour = true;
  state.stereoMix = 1;
  document.body.classList.add("golden-hour");
  el("featureBanner").classList.add("show");
  el("featureBanner").querySelector("strong").textContent = `${totalFs} GOLDEN HOUR SPINS`;
  el("fsCounter").hidden = false;
  renderHud();
  await wait(1100);
  el("featureBanner").classList.remove("show");
}

export function updateFreeSpins(current, total) {
  state.freeSpin = { current, total };
  el("fsCurrent").textContent = String(current);
  el("fsTotal").textContent = String(total);
}

export async function exitGoldenHour(amountCents) {
  el("featureBanner").classList.add("show");
  el("featureBanner").querySelector("strong").textContent =
    amountCents > 0 ? `ENCORE ${formatMoney(amountCents / 100)}` : "GOLDEN HOUR CLOSED";
  await wait(1200);
  el("featureBanner").classList.remove("show");
  el("fsCounter").hidden = true;
  state.goldenHour = false;
  state.stereoMix = 1;
  document.body.classList.remove("golden-hour");
  renderHud();
}

export function setStereoMix(value) {
  state.stereoMix = value;
  renderHud();
  el("mixPanel").classList.add("pulse");
  setTimeout(() => el("mixPanel").classList.remove("pulse"), 360);
}

export function markScatters(positions) {
  positions.forEach((pos) => {
    const cell = document.querySelector(`.cell[data-reel="${pos.reel}"][data-row="${pos.row - 1}"]`);
    if (cell) cell.classList.add("scatter");
  });
}

export function chargeBet(multiplier = 1) {
  const cost = state.bet * multiplier;
  if (state.balance < cost) return false;
  state.balance -= cost;
  state.win = 0;
  renderHud();
  return true;
}
