import { createActor, createMachine } from "xstate";
import { playBookEvents } from "./playBook";
import { runtime } from "./context";
import { cancelBonusIntro, hideSpinWin, stopAutoplay, ui } from "../lib/ui.svelte";
import { unlockMusic } from "../lib/music";
import { createEngineHandle, fetchReplayBook, type EngineHandle, type BookState } from "../rgs/session";
import { roundModeFlags, roundStakeAmount, stakeFromAuthenticate } from "../rgs/roundStake.js";
import { BUY_BONUS, BUY_SCATTER, BUY_WILD_BONUS } from "../math/config.js";
import type { Round } from "stake-engine";

export const betMachine = createMachine({
  id: "bet",
  initial: "idle",
  states: {
    idle: { on: { PLAY: "playing" } },
    playing: { on: { SETTLE: "idle" } },
  },
});

export const betActor = createActor(betMachine).start();

let engine: EngineHandle | null = null;
let replayBook: BookState | null = null;
let listening = false;
let pendingRestore: Round | null = null;

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message && error.message !== "[object Object]") {
    return error.message;
  }
  if (typeof error === "string") return error;
  return fallback;
}

async function waitForBoard(timeoutMs = 20000) {
  const started = Date.now();
  while (!runtime.board) {
    if (Date.now() - started > timeoutMs) {
      throw new Error("Reels failed to load.");
    }
    await new Promise((resolve) => setTimeout(resolve, 40));
  }
}

function applyRoundBet(round: Round) {
  const amount = roundStakeAmount(round);
  if (amount != null) ui.betMicro = amount;
}

function applyRestoredRound(round: Round) {
  applyRoundBet(round);
  const flags = roundModeFlags(round.mode);
  ui.scatterBuyOn = flags.scatterBuyOn;
  ui.wildBonus = flags.wildBonus;
}

function listenForEngineEvents() {
  if (listening) return;
  listening = true;
  window.addEventListener("balanceUpdate", ((event: CustomEvent<{ amount: number; currency?: string }>) => {
    if (!event.detail) return;
    ui.balanceMicro = event.detail.amount;
    if (event.detail.currency) ui.currency = event.detail.currency;
  }) as EventListener);
}

export async function bootEngine() {
  engine = createEngineHandle();
  ui.source = engine.kind;
  ui.replay = engine.query.replay;
  ui.social = engine.query.social || ui.social;
  if (engine.query.currency) ui.currency = engine.query.currency;
  if (engine.query.amount) {
    const amount = Number(engine.query.amount);
    if (Number.isFinite(amount) && amount > 0) ui.betMicro = amount;
  }

  await waitForBoard();
  listenForEngineEvents();

  if (engine.query.replay) {
    replayBook = await fetchReplayBook(engine.query);
    ui.ready = true;
    ui.banner = "";
    return;
  }

  const auth = await engine.Authenticate();
  ui.balanceMicro = auth.balance.amount;
  ui.currency = auth.balance.currency;
  ui.betLevels = auth.config.betLevels?.length ? auth.config.betLevels : ui.betLevels;
  ui.betMicro = stakeFromAuthenticate(auth) || ui.betLevels[0];
  ui.social = auth.jurisdictionFlags.socialCasino || engine.query.social;
  ui.disableSpacebar = auth.jurisdictionFlags.disabledSpacebar;
  ui.disableBuyFeature = Boolean(auth.jurisdictionFlags.disabledBuyFeature);
  ui.disableAutoplay = Boolean(auth.jurisdictionFlags.disabledAutoplay);
  if (auth.round?.active) {
    pendingRestore = auth.round;
    applyRestoredRound(auth.round);
  }
  ui.ready = true;
}

export async function playPendingRestore() {
  if (!pendingRestore || !engine) return;
  const round = pendingRestore;
  pendingRestore = null;
  ui.busy = true;
  try {
    applyRestoredRound(round);
    await playEngineRound(round);
    const ended = await engine.EndRound();
    ui.balanceMicro = ended.balance.amount;
  } finally {
    ui.busy = false;
  }
}

const MODE_COST: Record<string, number> = {
  base: 1,
  scatter: BUY_SCATTER.cost,
  bonus: BUY_BONUS.cost,
  wildbonus: BUY_WILD_BONUS.cost,
};

async function playEngineRound(round: Round) {
  await waitForBoard();
  applyRoundBet(round);
  const book = engine!.bookFromRound(round);
  ui.winMicro = 0;
  ui.banner = "";
  hideSpinWin();
  await playBookEvents(book.events);
}

export async function playBet(mode = "base") {
  unlockMusic();
  if (ui.busy || !ui.ready || ui.bootOpen || betActor.getSnapshot().matches("playing")) return false;
  if (!runtime.board) {
    ui.banner = "Reels are still loading.";
    return false;
  }
  if (ui.replay) {
    return playReplay();
  }
  if (!engine) {
    ui.banner = "Engine is not ready.";
    return false;
  }

  ui.busy = true;
  if (ui.autoplayOn) ui.autoplayLeft = Math.max(0, ui.autoplayLeft - 1);
  ui.banner = "";
  ui.feature = false;
  ui.wildBonus = mode === "wildbonus";
  ui.fsCurrent = 0;
  ui.fsTotal = 0;
  ui.winMicro = 0;
  ui.buyMenuOpen = false;
  ui.buyConfirm = "";
  ui.trayOpen = false;
  hideSpinWin();
  cancelBonusIntro();
  betActor.send({ type: "PLAY" });

  try {
    const result = await engine.Play({ amount: ui.betMicro, mode });
    ui.balanceMicro = result.balance.amount;
    await playEngineRound(result.round);
    if (result.round.active) {
      const ended = await engine.EndRound();
      ui.balanceMicro = ended.balance.amount;
    }
    if (import.meta.env.VITE_VPS === "1") {
      const cost = MODE_COST[mode] ?? 1;
      window.dispatchEvent(
        new CustomEvent("vps-stats-round", {
          detail: {
            spentMicro: Math.round(result.round.amount * cost),
            wonMicro: Math.max(0, Math.round(result.round.payout) || 0),
          },
        }),
      );
    }
    ui.banner = "";
    return true;
  } catch (error) {
    console.error(error);
    ui.banner = errorMessage(error, mode === "bonus" || mode === "wildbonus" ? "Buy failed." : "Spin failed.");
    ui.feature = false;
    ui.wildBonus = false;
    stopAutoplay();
    return false;
  } finally {
    ui.busy = false;
    betActor.send({ type: "SETTLE" });
  }
}

export async function playBuyBonus() {
  return playBet("bonus");
}

export async function playBuyWildBonus() {
  return playBet("wildbonus");
}

export async function playReplay() {
  unlockMusic();
  if (ui.bootOpen || !replayBook || !runtime.board) return false;
  ui.busy = true;
  ui.winMicro = 0;
  ui.banner = "";
  hideSpinWin();
  cancelBonusIntro();
  betActor.send({ type: "PLAY" });
  try {
    await playBookEvents(replayBook.events);
    ui.banner = "";
    return true;
  } catch (error) {
    ui.banner = errorMessage(error, "Replay failed.");
    return false;
  } finally {
    ui.busy = false;
    betActor.send({ type: "SETTLE" });
  }
}
