import { createActor, createMachine } from "xstate";
import { playRound } from "../math/math.js";
import { runtime } from "./context";
import { ui, charge } from "../lib/ui.svelte";

export const betMachine = createMachine({
  id: "bet",
  initial: "idle",
  states: {
    idle: { on: { PLAY: "playing" } },
    playing: { on: { SETTLE: "idle" } },
  },
});

export const betActor = createActor(betMachine).start();

export async function playBet() {
  if (ui.busy || betActor.getSnapshot().matches("playing")) return false;
  if (!runtime.board) {
    ui.banner = "Reels are still loading.";
    return false;
  }
  if (!charge(1)) {
    ui.banner = "Not enough credit.";
    return false;
  }

  ui.busy = true;
  ui.banner = "";
  ui.feature = false;
  ui.fsCurrent = 0;
  ui.fsTotal = 0;
  betActor.send({ type: "PLAY" });

  try {
    const round = playRound({
      seed: Date.now() ^ Math.floor(Math.random() * 1e9),
      bet: ui.bet,
    });
    let shown = 0;
    await runtime.board.playRound(round, {
      onBaseSettled() {
        shown = round.baseWin;
        ui.win = shown;
      },
      onBonusStart() {
        ui.feature = true;
        ui.fsTotal = round.bonusAwarded;
        ui.fsCurrent = 0;
        ui.banner = "3 suns — 10 extra plays";
      },
      onBonusSpinStart(index, total) {
        ui.fsCurrent = index + 1;
        ui.banner = `Extra play ${index + 1} / ${total}`;
      },
      onBonusSpinPaid(_index, _total, paidWin) {
        shown += paidWin;
        ui.win = Math.min(shown, round.totalWin);
      },
      onBonusEnd() {
        ui.feature = false;
        ui.fsCurrent = 0;
        ui.fsTotal = 0;
      },
    });
    ui.win = round.totalWin;
    if (round.totalWin > 0) {
      ui.balance += round.totalWin;
      const ways = Math.round(round.totalWays || round.wins.reduce((sum, win) => sum + win.ways, 0));
      ui.banner = round.bonusAwarded
        ? `Paid ${round.totalWin.toFixed(2)} · extra plays ${round.bonusWin.toFixed(2)}`
        : `Paid ${round.totalWin.toFixed(2)} · ${ways} ways`;
    } else {
      ui.banner = "";
    }
    return true;
  } catch (error) {
    console.error(error);
    ui.banner = error instanceof Error ? error.message : "Spin failed.";
    ui.feature = false;
    ui.fsCurrent = 0;
    ui.fsTotal = 0;
    return false;
  } finally {
    ui.busy = false;
    betActor.send({ type: "SETTLE" });
  }
}
