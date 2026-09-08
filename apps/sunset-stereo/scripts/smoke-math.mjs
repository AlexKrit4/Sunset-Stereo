import { playRound } from "../src/math/math.js";

const book = playRound({ seed: 1, buyBonus: false });
const bonus = playRound({ seed: 7, buyBonus: true });
const types = new Set(book.events.map((event) => event.type));
const bonusTypes = new Set(bonus.events.map((event) => event.type));

if (!types.has("reveal") || !types.has("finalWin")) {
  throw new Error(`base book missing core events: ${[...types]}`);
}
if (!bonusTypes.has("freeSpinTrigger") || !bonusTypes.has("updateGlobalMult")) {
  throw new Error(`bonus book missing feature events: ${[...bonusTypes]}`);
}

process.stdout.write(
  JSON.stringify(
    {
      base: book.events.map((event) => event.type),
      bonusCount: bonus.events.length,
      bonusHead: bonus.events.slice(0, 8).map((event) => event.type),
    },
    null,
    2,
  ) + "\n",
);
