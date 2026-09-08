import { playRound } from "../src/math/math.js";
import { REEL_ROWS, XNUDGE_REELS, XWAYS_REELS, SCATTER_REELS, PAYABLE } from "../src/math/config.js";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

const round = playRound({ seed: 1, bet: 1 });

assert(Array.isArray(round.raw) && round.raw.length === 6, "expected 6 reels");
assert(
  round.raw.every((col, i) => col.length === REEL_ROWS[i]),
  `row layout must be ${REEL_ROWS}`,
);
assert(!("events" in round), "base round must not emit book events");
assert(!("freeGameWins" in round), "bonus spins were not ported");
assert(typeof round.totalWin === "number", "totalWin missing");
assert(Array.isArray(round.waysGaps) && round.waysGaps.length === 6, "waysGaps missing");
assert(Array.isArray(round.scatterGaps) && round.scatterGaps.length === 6, "scatterGaps missing");

for (let i = 0; i < 400; i += 1) {
  const sample = playRound({ seed: 1000 + i, bet: 1 });
  sample.raw.forEach((col, reel) => {
    const wilds = col.filter((cell) => cell === "wild");
    assert(wilds.length === 0, `wilds must not land randomly (seed ${1000 + i} reel ${reel})`);
    const xWays = col.filter((cell) => cell === "xWays").length;
    if (xWays) assert(XWAYS_REELS.includes(reel), `xWays only on reels 2 and 5, got reel ${reel + 1}`);
    const xNudge = col.filter((cell) => cell === "xNudge").length;
    if (xNudge) {
      assert(XNUDGE_REELS.includes(reel), `xNudge only on reels 3 and 4, got reel ${reel + 1}`);
      for (let row = 0; row < xNudge; row += 1) {
        assert(col[row] === "xNudge", "xNudge stack must start at the top row");
      }
    }
    const scatters = col.filter((cell) => cell === "scatter").length;
    if (scatters) {
      assert(SCATTER_REELS.includes(reel), `scatter only on reels 2-5, got reel ${reel + 1}`);
      assert(scatters === 1, "max one scatter per reel");
    }
  });
  assert(sample.scatterCount < 99, "scatterCount present");
  sample.xWays.positions.forEach((pos) => {
    assert(XWAYS_REELS.includes(pos.reel), "resolved xWays off-lane");
    assert(PAYABLE.includes(pos.replacement), "xWays must become a payable");
    assert(pos.mult >= 2 && pos.mult <= 6, "xWays cell mult 2-6");
  });
  sample.nudge.forEach((step) => {
    assert(XNUDGE_REELS.includes(step.reel), "nudge off-lane");
    assert(step.mult >= 1, "nudge mult");
    assert(sample.resolved[step.reel].every((cell) => cell === "wild"), "nudge reel must become wilds");
  });
  if (sample.scatterCount >= 3) {
    assert(!sample.freeSpins, "3+ scatters must not start extra spins");
  }
}

const fullStack = (() => {
  for (let seed = 0; seed < 8000; seed += 1) {
    const sample = playRound({ seed, bet: 1 });
    const hit = sample.nudge.find((step) => step.landVisible === 4);
    if (hit) return hit;
  }
  return null;
})();
if (fullStack) {
  assert(fullStack.nudges === 0, "full xNudge stack does not push");
  assert(fullStack.mult === 4, "full xNudge stack pays x4");
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
