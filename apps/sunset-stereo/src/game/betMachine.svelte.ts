import { createActor, createMachine } from "xstate";
import { playBookEvents } from "./playBook";
import { runtime } from "./context";
import { moneyPlain, ui } from "../lib/ui.svelte";
import { createEngineHandle, fetchReplayBook, type EngineHandle, type BookState } from "../rgs/session";
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
    ui.banner = "Replay ready";
    return;
  }

  const auth = await engine.Authenticate();
  ui.balanceMicro = auth.balance.amount;
  ui.currency = auth.balance.currency;
  ui.betLevels = auth.config.betLevels?.length ? auth.config.betLevels : ui.betLevels;
  ui.betMicro = auth.config.defaultBetLevel || ui.betLevels[0];
  ui.social = auth.jurisdictionFlags.socialCasino || engine.query.social;
  ui.disableSpacebar = auth.jurisdictionFlags.disabledSpacebar;
  if (auth.round?.active) {
    ui.ready = true;
    await playEngineRound(auth.round);
    const ended = await engine.EndRound();
    ui.balanceMicro = ended.balance.amount;
  }
  ui.ready = true;
}

async function playEngineRound(round: Round) {
  await waitForBoard();
  const book = engine!.bookFromRound(round);
  ui.winMicro = 0;
  ui.banner = "";
  await playBookEvents(book.events);
}

export async function playBet() {
  if (ui.busy || !ui.ready || betActor.getSnapshot().matches("playing")) return false;
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
  ui.banner = "";
  ui.feature = false;
  ui.fsCurrent = 0;
  ui.fsTotal = 0;
  ui.winMicro = 0;
  betActor.send({ type: "PLAY" });

  try {
    const result = await engine.Play({ amount: ui.betMicro, mode: "base" });
    ui.balanceMicro = result.balance.amount;
    await playEngineRound(result.round);
    if (result.round.active) {
      const ended = await engine.EndRound();
      ui.balanceMicro = ended.balance.amount;
    }
    ui.banner = ui.winMicro ? `Paid ${moneyPlain(ui.winMicro)}` : "";
    return true;
  } catch (error) {
    console.error(error);
    ui.banner = errorMessage(error, "Spin failed.");
    ui.feature = false;
    return false;
  } finally {
    ui.busy = false;
    betActor.send({ type: "SETTLE" });
  }
}

export async function playReplay() {
  if (!replayBook || !runtime.board) return false;
  ui.busy = true;
  ui.winMicro = 0;
  ui.banner = "";
  betActor.send({ type: "PLAY" });
  try {
    await playBookEvents(replayBook.events);
    ui.banner = ui.winMicro ? `Replay paid ${moneyPlain(ui.winMicro)}` : "Replay complete";
    return true;
  } catch (error) {
    ui.banner = errorMessage(error, "Replay failed.");
    return false;
  } finally {
    ui.busy = false;
    betActor.send({ type: "SETTLE" });
  }
}
