import {
  applyVpsRound,
  chartPoints,
  emptyVpsStats,
  loadVpsStats,
  saveVpsStats,
  vpsNet,
  vpsRtp,
} from "../src/vps/stats.js";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

const empty = emptyVpsStats();
assert(empty.spins === 0 && empty.spentMicro === 0 && empty.wonMicro === 0, "empty stats start at zero");

const first = applyVpsRound(empty, 1_000_000, 0);
assert(first.spins === 1 && first.spentMicro === 1_000_000 && first.wonMicro === 0, "first spin records the stake");
assert(vpsNet(first) === -1_000_000, "dead spin is negative net");
assert(vpsRtp(first) === 0, "dead spin RTP is 0");

const second = applyVpsRound(first, 1_000_000, 2_500_000);
assert(second.spins === 2 && second.spentMicro === 2_000_000 && second.wonMicro === 2_500_000, "second spin adds spend and win");
assert(vpsNet(second) === 500_000, "net is won minus spent");
assert(Math.abs(vpsRtp(second) - 1.25) < 1e-9, "RTP is won / spent");
assert(second.history.at(-1).net === 500_000, "history stores cumulative net");

const storage = new Map();
const fake = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
};
saveVpsStats(fake, second);
const loaded = loadVpsStats(fake);
assert(loaded.spins === 2 && loaded.wonMicro === 2_500_000, "stats persist");

const chart = chartPoints(second.history, 220, 72);
assert(chart.points.includes(","), "chart emits svg points");
assert(chart.max >= chart.min, "chart range is ordered");

let many = emptyVpsStats();
for (let i = 0; i < 200; i += 1) many = applyVpsRound(many, 100, i % 3 === 0 ? 250 : 0);
assert(many.history.length === 180, "history keeps a rolling window");

console.log("vps stats ok");
