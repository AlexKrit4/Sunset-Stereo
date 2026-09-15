import { duckMusicBed, restoreMusicBed } from "./music";
import { ui } from "./ui.svelte";
import { waitForTimeout } from "../utils/waitForTimeout";
import {
  BIG_WIN_MULT,
  BIG_WIN_STAGES,
  isBigWin as isBigWinAt,
  stagesForWin as stagesForWinAt,
} from "./bigWinStages.js";

export { BIG_WIN_MULT, BIG_WIN_STAGES };

export function isBigWin(micro: number, betMicro = ui.betMicro) {
  return isBigWinAt(micro, betMicro);
}

export function stagesForWin(micro: number, betMicro = ui.betMicro) {
  return stagesForWinAt(micro, betMicro);
}

const STAGE_MS = 8000;
const BZZZ_TO_START_MS = 2500;
const OUTGOING_MS = 720;
const EXPLODE_MS = 720;
const START_FALLBACK_MS = 20000;
const END_FALLBACK_MS = 8000;

const clips: HTMLAudioElement[] = [];

function audioUrl(file: string) {
  return `${import.meta.env.BASE_URL}audio/bigwin/${file}`;
}

function easeOutQuart(progress: number) {
  if (progress >= 1) return 1;
  if (progress <= 0) return 0;
  return 1 - (1 - progress) ** 4;
}

function stopClips() {
  clips.splice(0).forEach((clip) => {
    clip.pause();
    clip.src = "";
  });
}

function playClip(file: string, volume = 1) {
  const clip = new Audio(audioUrl(file));
  clip.preload = "auto";
  clip.volume = ui.musicMuted ? 0 : volume;
  clips.push(clip);
  const playing = clip.play().then(() => true).catch(() => false);
  return { clip, playing };
}

async function waitForClipEnd(
  clip: HTMLAudioElement,
  playing: Promise<boolean>,
  fallbackMs: number,
) {
  const ok = await playing;
  if (!ok || clip.error) return;
  await new Promise<void>((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      resolve();
    };
    const timer = window.setTimeout(done, fallbackMs);
    clip.addEventListener("ended", done, { once: true });
    clip.addEventListener("error", done, { once: true });
    if (clip.ended || clip.error) done();
  });
}

function countStage(fromMicro: number, toMicro: number, ms: number) {
  return new Promise<void>((resolve) => {
    const started = performance.now();
    const tick = (now: number) => {
      if (!ui.bigWinOpen) {
        resolve();
        return;
      }
      const progress = Math.min(1, (now - started) / ms);
      ui.bigWinDisplayMicro = Math.round(fromMicro + (toMicro - fromMicro) * easeOutQuart(progress));
      if (progress < 1) {
        requestAnimationFrame(tick);
        return;
      }
      ui.bigWinDisplayMicro = toMicro;
      resolve();
    };
    ui.bigWinDisplayMicro = fromMicro;
    requestAnimationFrame(tick);
  });
}

function showStageTitle(left: string, right: string) {
  if (ui.bigWinLeft) {
    ui.bigWinOutgoingLeft = ui.bigWinLeft;
    ui.bigWinOutgoingRight = ui.bigWinRight;
    ui.bigWinOutgoingKey += 1;
    const key = ui.bigWinOutgoingKey;
    window.setTimeout(() => {
      if (ui.bigWinOutgoingKey === key) {
        ui.bigWinOutgoingLeft = "";
        ui.bigWinOutgoingRight = "";
      }
    }, OUTGOING_MS);
  }
  ui.bigWinExplode = false;
  ui.bigWinLeft = left;
  ui.bigWinRight = right;
  ui.bigWinTitleKey += 1;
}

function resetOverlay() {
  ui.bigWinOpen = false;
  ui.bigWinExplode = false;
  ui.bigWinLeft = "";
  ui.bigWinRight = "";
  ui.bigWinOutgoingLeft = "";
  ui.bigWinOutgoingRight = "";
  ui.bigWinDisplayMicro = 0;
}

export async function playBigWin(micro: number) {
  const stages = stagesForWin(micro, ui.betMicro);
  if (!stages.length) return;

  duckMusicBed();
  ui.bigWinOpen = true;
  ui.bigWinExplode = false;
  ui.bigWinLeft = "";
  ui.bigWinRight = "";
  ui.bigWinOutgoingLeft = "";
  ui.bigWinOutgoingRight = "";
  ui.bigWinDisplayMicro = stages[0].fromMicro;

  playClip("bzzz.mp3");
  await waitForTimeout(BZZZ_TO_START_MS);
  const start = playClip("start.mp3");
  await waitForClipEnd(start.clip, start.playing, START_FALLBACK_MS);

  for (const stage of stages) {
    showStageTitle(stage.left, stage.right);
    const track = playClip(stage.file);
    await countStage(stage.fromMicro, stage.toMicro, STAGE_MS);
    track.clip.pause();
  }

  ui.bigWinExplode = true;
  const end = playClip("end.mp3");
  await Promise.all([
    waitForClipEnd(end.clip, end.playing, END_FALLBACK_MS),
    waitForTimeout(EXPLODE_MS),
  ]);

  stopClips();
  resetOverlay();
  restoreMusicBed();
}
