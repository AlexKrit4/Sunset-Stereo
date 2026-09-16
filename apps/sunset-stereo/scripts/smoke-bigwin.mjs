import { BIG_WIN_STAGES, followingWincap, isBigWin, stagesForWin, wincapStageWin } from "../src/lib/bigWinStages.js";

function assert(cond, message) {
  if (!cond) throw new Error(message);
}

const bet = 1_000_000;

assert(BIG_WIN_STAGES.map((stage) => stage.id).join(",") === "win1,win2,win3,win4,win5", "five stages");
assert(!isBigWin(20 * bet, bet), "exactly 20x is not a big win");
assert(isBigWin(20 * bet + 1, bet), "just over 20x is a big win");

function ids(micro) {
  return stagesForWin(micro, bet).map((stage) => stage.id).join(",");
}

assert(ids(20 * bet) === "win1", "20x sits inside the 0-40 band");
assert(ids(30 * bet) === "win1", "30x stays on win1 then end");
assert(ids(40 * bet) === "win1", "40x is the top of win1");
assert(ids(40 * bet + 1) === "win1,win2", "just over 40x enters win2");
assert(ids(50 * bet) === "win1,win2", "50x uses win1 then win2");
assert(ids(60 * bet) === "win1,win2", "60x is the top of win2");
assert(ids(80 * bet) === "win1,win2,win3", "80x is the top of win3");
assert(ids(200 * bet) === "win1,win2,win3,win4", "200x is the top of win4");
assert(ids(201 * bet) === "win1,win2,win3,win4,win5", "over 200x reaches sunset");

const win1 = stagesForWin(30 * bet, bet)[0];
assert(win1.fromMicro === 0, "win1 counter starts at 0x");
assert(win1.toMicro === 30 * bet, "30x counts only to the actual win");

const mid = stagesForWin(50 * bet, bet);
assert(mid[0].toMicro === 40 * bet, "win1 fills to its 40x cap");
assert(mid[1].fromMicro === 40 * bet, "win2 restarts the counter at 40x");
assert(mid[1].toMicro === 50 * bet, "win2 stops at the actual win");

const sunset = stagesForWin(250 * bet, bet);
assert(sunset.at(-1).id === "win5", "final stage is sunset");
assert(sunset.at(-1).fromMicro === 200 * bet, "win5 starts at 200x");
assert(sunset.at(-1).toMicro === 250 * bet, "win5 counts through to the actual win");

const cap = stagesForWin(15000 * bet, bet);
assert(ids(15000 * bet) === "win1,win2,win3,win4,win5", "15000x max win uses every stage");
assert(cap.at(-1).toMicro === 15000 * bet, "sunset stage counts through to 15000x");

const already = 2307 * bet;
const remainder = 15000 * bet - already;
assert(wincapStageWin(15000 * bet, remainder, already) === remainder, "wincap stages use 15000x minus paid total");
assert(wincapStageWin(15000 * bet, 15000 * bet, 0) === 15000 * bet, "a first-spin max win still counts the full cap");

const capSpin = stagesForWin(remainder, bet);
assert(capSpin.map((stage) => stage.id).join(",") === "win1,win2,win3,win4,win5", "remaining 12693x still plays every stage");
assert(capSpin[0].fromMicro === 0 && capSpin[0].toMicro === 40 * bet, "win1 still counts 0-40x");
assert(capSpin.at(-1).id === "win5", "last stage is sunset");
assert(capSpin.at(-1).fromMicro === 200 * bet, "sunset starts at 200x");
assert(capSpin.at(-1).toMicro === remainder, "sunset ends at 15000x minus the paid 2307x");

const mathWincap = [
  { index: 0, type: "winInfo", totalWin: 1_269_300 },
  { index: 1, type: "wincap", amount: 1_500_000 },
  { index: 2, type: "setTotalWin", amount: 1_500_000 },
  { index: 3, type: "freeSpinEnd", amount: 1_500_000 },
  { index: 4, type: "finalWin", amount: 1_500_000 },
];
assert(followingWincap(mathWincap, mathWincap[0])?.type === "wincap", "math books emit wincap right after winInfo");

const demoWincap = [
  { index: 0, type: "winInfo", totalWin: 1_500_000 },
  { index: 1, type: "setWin", amount: 1_269_300 },
  { index: 2, type: "setTotalWin", amount: 1_500_000 },
  { index: 3, type: "wincap", amount: 1_500_000 },
];
assert(followingWincap(demoWincap, demoWincap[1])?.amount === 1_500_000, "demo books still expose wincap after setWin");

const laterSpin = [
  { index: 0, type: "setWin", amount: 80_000 },
  { index: 1, type: "setTotalWin", amount: 230_700 },
  { index: 2, type: "updateFreeSpin", amount: 4, total: 10 },
  { index: 3, type: "wincap", amount: 1_500_000 },
];
assert(followingWincap(laterSpin, laterSpin[0]) == null, "a later extra play wincap does not attach to this setWin");

console.log("bigwin stages ok");
