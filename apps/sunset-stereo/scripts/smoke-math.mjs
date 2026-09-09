import { playRound } from "../src/math/math.js";
import { BONUS_SPINS, SCATTER_REELS, SCATTER_REEL_LAND_CHANCE } from "../src/math/config.js";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

function keyOf(pos) {
  return `${pos.reel}:${pos.row}`;
}

const round = playRound({ seed: 1, bet: 1 });

assert(Array.isArray(round.raw) && round.raw.length === 6, "expected 6 reels");
assert(
  round.raw.every((col) => col.length === 4),
  "row layout must be 6x4",
);
assert(!("events" in round), "base round must not emit book events");
assert(typeof round.totalWin === "number", "totalWin missing");
assert(Array.isArray(round.waysGaps) && round.waysGaps.length === 6, "waysGaps missing");
assert(Array.isArray(round.scatterGaps) && round.scatterGaps.length === 6, "scatterGaps missing");
assert(typeof round.bonusAwarded === "number", "bonusAwarded missing");
assert(Array.isArray(round.bonusSpins), "bonusSpins missing");

let bonusHits = 0;
let samples = 0;
for (let i = 0; i < 8000; i += 1) {
  const sample = playRound({ seed: 1000 + i, bet: 1 });
  samples += 1;
  sample.raw.forEach((col, reel) => {
    assert(col.length === 4, `reel ${reel} must have 4 rows`);
    assert(col.every((cell) => cell !== "wild"), `wilds must not land (seed ${1000 + i} reel ${reel})`);
    assert(col.every((cell) => cell !== "xWays"), `xWays disabled (seed ${1000 + i} reel ${reel})`);
    assert(col.every((cell) => cell !== "xNudge"), `xNudge disabled (seed ${1000 + i} reel ${reel})`);
    sample.resolved[reel].forEach((cell) => {
      assert(cell !== "wild", `resolved wilds must not appear (seed ${1000 + i} reel ${reel})`);
      assert(cell !== "xWays", `resolved xWays must not appear (seed ${1000 + i} reel ${reel})`);
      assert(cell !== "xNudge", `resolved xNudge must not appear (seed ${1000 + i} reel ${reel})`);
    });
    const scatters = col.filter((cell) => cell === "scatter").length;
    if (scatters) {
      assert(SCATTER_REELS.includes(reel), `scatter only on reels 2-5, got reel ${reel + 1}`);
      assert(scatters === 1, "max one scatter per reel");
    }
  });
  assert(sample.xWays.positions.length === 0, "xWays must not resolve");
  assert(sample.nudge.length === 0, "nudge must not resolve");
  if (sample.scatterCount >= 3) {
    bonusHits += 1;
    assert(sample.bonusAwarded === BONUS_SPINS, `3+ scatters must start ${BONUS_SPINS} extra plays`);
    assert(sample.bonusSpins.length === BONUS_SPINS, "bonus must run exactly 10 spins");
    for (const spin of sample.bonusSpins) {
      assert(spin.steps.length >= 1, "each extra play needs a land");
      spin.steps.forEach((step) => {
        step.board.forEach((col) => {
          assert(col.every((cell) => cell !== "scatter"), "bonus boards omit scatters");
        });
      });
      if (spin.paidWin <= 0) {
        assert(spin.steps.length === 1, "dead extra play must not respin");
        continue;
      }
      const first = spin.steps[0];
      assert(first.totalWin > 0, "paid extra play must start with a win");
      if (first.locked.length < 24) {
        assert(spin.steps.length >= 2, "winning extra play must respin before paying");
      }
      const last = spin.steps[spin.steps.length - 1];
      assert(last.totalWin === spin.paidWin, "pay the last hold-respin board");
      if (spin.steps.length >= 2 && spin.steps.length - 1 < 16) {
        const prevLocked = new Set(spin.steps[spin.steps.length - 2].locked.map(keyOf));
        const grown = last.highlights.some((pos) => !prevLocked.has(keyOf(pos)));
        const allLocked = last.locked.length >= 24;
        assert(!grown || allLocked, "bonus spin must stop when a respin adds no new winning cells");
      }
    }
  } else {
    assert(sample.bonusAwarded === 0, "fewer than 3 scatters must not start extra plays");
    assert(sample.bonusSpins.length === 0, "no bonus spins without a trigger");
  }
}

assert(SCATTER_REEL_LAND_CHANCE === 0.12, "bonus chance is tuned at p=0.12 (~1/159)");
const hit = samples / bonusHits;
assert(bonusHits > 0, "expected some 3-scatter bonus triggers in 8000 spins");
assert(
  hit >= 100 && hit <= 250,
  `bonus hit rate 1 in ${hit.toFixed(1)} (p=${SCATTER_REEL_LAND_CHANCE}) should sit near 1 in 150-180`,
);

process.stdout.write(
  JSON.stringify(
    {
      reels: round.raw.map((col) => col.length),
      win: round.totalWin,
      ways: round.totalWays,
      xWays: round.xWays.positions.length,
      nudge: round.nudge,
      scatters: round.scatterCount,
      bonusAwarded: round.bonusAwarded,
      extraStopMs: round.extraStopMs,
      bonusHits,
      samples,
      hitRate: bonusHits ? Number((samples / bonusHits).toFixed(1)) : null,
    },
    null,
    2,
  ) + "\n",
);
