import { DisplayAmount, ParseAmount } from "stake-engine";
import type { Currency } from "stake-engine";
import { ui } from "../lib/ui.svelte";

/** RGS wallet unit: 1.00 → 1_000_000. Not re-exported from stake-engine's JS bundle. */
export const API_MULTIPLIER = 1_000_000;

export { ParseAmount };

export function formatMoney(micro: number) {
  try {
    return DisplayAmount(
      { amount: micro, currency: (ui.currency || "USD") as Currency },
      { removeSymbol: false },
    );
  } catch {
    return (micro / API_MULTIPLIER).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
}

export function formatMoneyPlain(micro: number) {
  return (micro / API_MULTIPLIER).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function multiplierCentsToMicro(cents: number, betMicro = ui.betMicro) {
  return Math.round((cents / 100) * betMicro);
}
