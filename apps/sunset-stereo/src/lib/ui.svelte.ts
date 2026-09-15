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
  spinWinLines: 0,
  betLevels: [0.1, 0.2, 0.5, 1, 2, 5, 10, 25].map((value) => value * API_MULTIPLIER),
  busy: false,
  mix: 1,
  feature: false,
  fsCurrent: 0,
  fsTotal: 0,
  banner: "",
  rulesOpen: false,
  bonusIntroOpen: false,
  bonusIntroSpins: 0,
  disableSpacebar: false,
  disableBuyFeature: false,
  musicMuted: false,
  buyMenuOpen: false,
  scatterBuyOn: false,
  buyConfirm: "" as "" | "scatter" | "bonus" | "wildbonus",
  wildBonus: false,
  trayOpen: false,
  autoplayOn: false,
  disableAutoplay: false,
  bigWinOpen: false,
  bigWinDisplayMicro: 0,
  bigWinLeft: "",
  bigWinRight: "",
  bigWinTitleKey: 0,
  bigWinOutgoingLeft: "",
  bigWinOutgoingRight: "",
  bigWinOutgoingKey: 0,
  bigWinExplode: false,
  bootOpen: true,
  bootReady: false,
  bootProgress: 0,
});

let bonusIntroResolve: (() => void) | null = null;

export function waitForBonusStart(totalFs: number) {
  ui.autoplayOn = false;
  ui.bonusIntroSpins = totalFs;
  ui.bonusIntroOpen = true;
  return new Promise<void>((resolve) => {
    bonusIntroResolve = resolve;
  });
}

export function confirmBonusStart() {
  ui.bonusIntroOpen = false;
  const resolve = bonusIntroResolve;
  bonusIntroResolve = null;
  resolve?.();
}

export function cancelBonusIntro() {
  ui.bonusIntroOpen = false;
  ui.bonusIntroSpins = 0;
  const resolve = bonusIntroResolve;
  bonusIntroResolve = null;
  resolve?.();
}

export const WIN_OVERLAY_MULT = 5;

export function showSpinWin(micro: number, lines = 0) {
  if (micro <= 0) {
    hideSpinWin();
    return;
  }
  ui.spinWinMicro = micro;
  ui.spinWinLines = lines;
  ui.spinWinVisible = true;
  ui.spinWinKey += 1;
}

export function hideSpinWin() {
  ui.spinWinVisible = false;
  ui.spinWinMicro = 0;
  ui.spinWinLines = 0;
}

export function roundWinBeatsStake(micro = ui.winMicro, multiple = WIN_OVERLAY_MULT) {
  return micro > ui.betMicro * multiple;
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
  if (ui.busy || ui.replay || ui.bootOpen) return;
  const index = ui.betLevels.indexOf(ui.betMicro);
  const next = Math.max(0, Math.min(ui.betLevels.length - 1, (index < 0 ? 0 : index) + delta));
  ui.betMicro = ui.betLevels[next];
}

export const labels = {
  credit: () => (ui.social ? "Balance" : "Credit"),
  paid: () => (ui.social ? "Won" : "Paid"),
  stake: () => (ui.social ? "Play amount" : "Stake"),
  spin: () => (ui.replay ? "Play" : ui.social ? "Play" : "Spin"),
  buy: () => (ui.social ? "Bonus" : "Buy"),
  buyBonus: () => (ui.social ? "Get bonus" : "Buy bonus"),
  buyNow: () => (ui.social ? "Get" : "Buy"),
  activate: () => "Activate",
  activated: () => "Active",
  win: () => (ui.social ? "Won" : "Win"),
  cancel: () => "Cancel",
  confirm: () => "Confirm",
  continue: () => "Continue",
};
