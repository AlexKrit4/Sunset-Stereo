import { playRound } from "../src/math/math.js";
import { SCATTER_REELS } from "../src/math/config.js";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

const round = playRound({ seed: 1, bet: 1 });

assert(Array.isArray(round.raw) && round.raw.length === 6, "expected 6 reels");
assert(
  round.raw.every((col) => col.length === 4),
  "row layout must be 6x4",
);
assert(!("events" in round), "base round must not emit book events");
assert(!("freeGameWins" in round), "bonus spins were not ported");
assert(typeof round.totalWin === "number", "totalWin missing");
assert(Array.isArray(round.waysGaps) && round.waysGaps.length === 6, "waysGaps missing");
assert(Array.isArray(round.scatterGaps) && round.scatterGaps.length === 6, "scatterGaps missing");

for (let i = 0; i < 400; i += 1) {
  const sample = playRound({ seed: 1000 + i, bet: 1 });
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
  assert(sample.scatterCount < 99, "scatterCount present");
  if (sample.scatterCount >= 3) {
    assert(!sample.freeSpins, "3+ scatters must not start extra spins");
  }
}

process.stdout.write(
  JSON.stringify(
    {
      reels: round.raw.map((col) => col.length),
      win: round.totalWin,
      ways: round.totalWays,
      xWays: round.xWays.positions.length,
      nudge: round.nudge,
      scatters: round.scatterCount,
      extraStopMs: round.extraStopMs,
    },
    null,
    2,
  ) + "\n",
);
