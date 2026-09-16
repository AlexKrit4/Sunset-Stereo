/**
 * Stake Engine authenticate may return the currently active round.
 * Frontends must continue that round, and wallet payouts are always
 * `payoutMultiplier × Play amount` — not `config.defaultBetLevel`.
 *
 * @see docs/ENGINE_DOCUMENTATION.md (Rgs Wallet authenticate; Bet Modes)
 */

export function roundStakeAmount(round) {
  const amount = Number(round?.amount);
  if (!Number.isFinite(amount) || amount <= 0) return null;
  return amount;
}

export function roundModeFlags(mode) {
  const key = String(mode || "base").toLowerCase();
  return {
    scatterBuyOn: key === "scatter",
    wildBonus: key === "wildbonus",
  };
}

export function stakeFromAuthenticate(auth) {
  const defaultBet = Number(auth?.config?.defaultBetLevel);
  const levels = Array.isArray(auth?.config?.betLevels) ? auth.config.betLevels : [];
  const fallback = Number.isFinite(defaultBet) && defaultBet > 0 ? defaultBet : Number(levels[0]) || 0;
  if (auth?.round?.active) {
    const restored = roundStakeAmount(auth.round);
    if (restored != null) return restored;
  }
  return fallback;
}

export function winMicroForStake(cents, stakeAmount) {
  return Math.round((cents / 100) * stakeAmount);
}
