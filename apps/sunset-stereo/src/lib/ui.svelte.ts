export const ui = $state({
  balance: 1000,
  bet: 1,
  win: 0,
  busy: false,
  mix: 1,
  feature: false,
  fsCurrent: 0,
  fsTotal: 0,
  banner: "",
  rulesOpen: false,
  paytableOpen: false,
});

export const BETS = [0.2, 0.4, 1, 2, 5, 10, 20, 50];
export const BUY_COST = 80;

export function money(value: number) {
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function changeBet(delta: number) {
  if (ui.busy) return;
  const index = BETS.indexOf(ui.bet);
  ui.bet = BETS[Math.max(0, Math.min(BETS.length - 1, index + delta))];
}

export function charge(mult: number) {
  const cost = ui.bet * mult;
  if (ui.balance < cost) return false;
  ui.balance -= cost;
  ui.win = 0;
  return true;
}

export function scaled(cents: number) {
  return (cents / 100) * ui.bet;
}
