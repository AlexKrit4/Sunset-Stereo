import { getContext as svelteGetContext, setContext as svelteSetContext } from "svelte";
import { eventEmitter } from "./eventEmitter";
import type { BoardController } from "../pixi/board";

const KEY = "sunset-stereo";

export type GameContext = {
  eventEmitter: typeof eventEmitter;
  board: BoardController | null;
};

export const runtime: GameContext = {
  eventEmitter,
  board: null,
};

export function setContext() {
  svelteSetContext(KEY, runtime);
}

export function getContext(): GameContext {
  return (svelteGetContext(KEY) as GameContext | undefined) ?? runtime;
}
