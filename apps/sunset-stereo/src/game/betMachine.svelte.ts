import { createActor, createMachine } from "xstate";
import { playRound } from "../math/math.js";
import { playBookEvents } from "./playBook";
import { ui, charge, BUY_COST } from "../lib/ui.svelte";

export const betMachine = createMachine({
  id: "bet",
  initial: "idle",
  states: {
    idle: {
      on: { PLAY: "playing" },
    },
    playing: {
      on: { SETTLE: "idle" },
    },
  },
});

export const betActor = createActor(betMachine).start();

export async function playBet(buyBonus = false) {
  if (ui.busy || betActor.getSnapshot().matches("playing")) return false;
  const costMult = buyBonus ? BUY_COST : 1;
  if (!charge(costMult)) {
    ui.banner = "Not enough credit.";
    return false;
  }

  ui.busy = true;
  ui.banner = buyBonus ? "Buying Golden Hour…" : "";
  betActor.send({ type: "PLAY" });

  try {
    const book = playRound({
      seed: Date.now() ^ Math.floor(Math.random() * 1e9),
      buyBonus,
    });
    await playBookEvents(book.events, { bookEvents: book.events });
    return true;
  } finally {
    ui.busy = false;
    betActor.send({ type: "SETTLE" });
  }
}
