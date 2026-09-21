export const VPS_STATS_KEY = "sunset-stereo-vps-stats";
export const VPS_STATS_HISTORY = 180;

export function emptyVpsStats() {
  return {
    spins: 0,
    spentMicro: 0,
    wonMicro: 0,
    history: [],
  };
}

export function applyVpsRound(stats, spentMicro, wonMicro) {
  const spent = Math.max(0, Math.round(spentMicro) || 0);
  const won = Math.max(0, Math.round(wonMicro) || 0);
  const next = {
    spins: stats.spins + 1,
    spentMicro: stats.spentMicro + spent,
    wonMicro: stats.wonMicro + won,
    history: stats.history.concat({
      n: stats.spins + 1,
      spent,
      won,
      net: stats.wonMicro + won - (stats.spentMicro + spent),
    }),
  };
  if (next.history.length > VPS_STATS_HISTORY) {
    next.history = next.history.slice(next.history.length - VPS_STATS_HISTORY);
  }
  return next;
}

export function vpsRtp(stats) {
  if (stats.spentMicro <= 0) return 0;
  return stats.wonMicro / stats.spentMicro;
}

export function vpsNet(stats) {
  return stats.wonMicro - stats.spentMicro;
}

export function loadVpsStats(storage) {
  try {
    const raw = storage?.getItem(VPS_STATS_KEY);
    if (!raw) return emptyVpsStats();
    const parsed = JSON.parse(raw);
    return {
      spins: Math.max(0, Number(parsed.spins) || 0),
      spentMicro: Math.max(0, Number(parsed.spentMicro) || 0),
      wonMicro: Math.max(0, Number(parsed.wonMicro) || 0),
      history: Array.isArray(parsed.history)
        ? parsed.history
            .map((row) => ({
              n: Number(row.n) || 0,
              spent: Math.max(0, Number(row.spent) || 0),
              won: Math.max(0, Number(row.won) || 0),
              net: Number(row.net) || 0,
            }))
            .slice(-VPS_STATS_HISTORY)
        : [],
    };
  } catch {
    return emptyVpsStats();
  }
}

export function saveVpsStats(storage, stats) {
  storage?.setItem(VPS_STATS_KEY, JSON.stringify(stats));
}

export function chartPoints(history, width, height, pad = 8) {
  if (!history.length) return { points: "", min: 0, max: 0 };
  const nets = history.map((row) => row.net);
  let min = Math.min(0, ...nets);
  let max = Math.max(0, ...nets);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const innerW = Math.max(1, width - pad * 2);
  const innerH = Math.max(1, height - pad * 2);
  const last = Math.max(1, history.length - 1);
  const pts = history.map((row, index) => {
    const x = pad + (index / last) * innerW;
    const y = pad + ((max - row.net) / (max - min)) * innerH;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return { points: pts.join(" "), min, max };
}
