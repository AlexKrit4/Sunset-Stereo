import { formatMoney, formatMoneyPlain } from "../rgs/money";
import { API_MULTIPLIER } from "../rgs/money";

export const ui = $state({
  ready: false,
  error: "",
  source: "mock" as "mock" | "live",
  replay: false,
  social: false,
  currency: "USD",
  balanceMicro: 1000 * API_MULTIPLIER,
  betMicro: API_MULTIPLIER,
  winMicro: 0,
  spinWinMicro: 0,
  spinWinVisible: false,
  spinWinKey: 0,
  betLevels: [0.1, 0.2, 0.5, 1, 2, 5, 10, 25].map((value) => value * API_MULTIPLIER),
  busy: false,
  mix: 1,
  feature: false,
  fsCurrent: 0,
  fsTotal: 0,
  banner: "",
  rulesOpen: false,
  disableSpacebar: false,
});

export function showSpinWin(micro: number) {
  if (micro <= 0) {
    hideSpinWin();
    return;
  }
  ui.spinWinMicro = micro;
  ui.spinWinVisible = true;
  ui.spinWinKey += 1;
}

export function hideSpinWin() {
  ui.spinWinVisible = false;
  ui.spinWinMicro = 0;
}

export function money(value: number) {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function moneyHud(micro: number) {
  return formatMoney(micro);
}

export function moneyPlain(micro: number) {
  return formatMoneyPlain(micro);
}

export function changeBet(delta: number) {
  if (ui.busy || ui.replay) return;
  const index = ui.betLevels.indexOf(ui.betMicro);
  const next = Math.max(0, Math.min(ui.betLevels.length - 1, (index < 0 ? 0 : index) + delta));
  ui.betMicro = ui.betLevels[next];
}

export const labels = {
  credit: () => (ui.social ? "Balance" : "Credit"),
  paid: () => (ui.social ? "Won" : "Paid"),
  stake: () => (ui.social ? "Play amount" : "Stake"),
  spin: () => (ui.replay ? "Play" : ui.social ? "Play" : "Spin"),
};
