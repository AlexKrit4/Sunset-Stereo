import { ui } from "./ui.svelte";

export const FAST_PLAY_SCALE = 0.4;

export function isFastPlay() {
  return ui.fastPlay;
}

export function paceMs(ms: number, floor = 16) {
  if (!ui.fastPlay) return ms;
  return Math.max(floor, Math.round(ms * FAST_PLAY_SCALE));
}
