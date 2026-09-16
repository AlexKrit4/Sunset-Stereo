import { duckMusicBed, restoreMusicBed } from "./music";
import { audioSrc } from "./audioBank";
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
const armed = new Map<string, HTMLAudioElement>();
let introActive = false;
let startFinished: Promise<void> = Promise.resolve();

function audioUrl(file: string) {
  return audioSrc(`audio/bigwin/${file}`);
}

function easeOutCount(progress: number) {
  if (progress >= 1) return 1;
  if (progress <= 0) return 0;
  return 1 - (1 - progress) ** 1.7;
}

function stopClips() {
  clips.splice(0).forEach((clip) => {
    clip.pause();
    clip.src = "";
  });
  armed.clear();
}

function makeClip(file: string) {
  const clip = new Audio(audioUrl(file));
  clip.preload = "auto";
  clip.playsInline = true;
  clip.setAttribute("playsinline", "true");
  clip.setAttribute("webkit-playsinline", "true");
  clip.volume = 0;
  clips.push(clip);
  return clip;
}

function armFile(file: string) {
  let clip = armed.get(file);
  if (clip) return clip;
  clip = makeClip(file);
  armed.set(file, clip);
  return clip;
}

async function warmFile(file: string) {
  const clip = armFile(file);
  try {
    clip.muted = true;
    clip.volume = 0;
    await clip.play();
    clip.pause();
    clip.currentTime = 0;
    clip.muted = false;
  } catch {
    /* ignore */
  }
  return clip;
}

function warmStageClips() {
  return Promise.all([...BIG_WIN_STAGES.map((stage) => stage.file), "end.mp3"].map(warmFile)).then(
    () => undefined,
  );
}

function startArmed(file: string, volume = 1) {
  const clip = armFile(file);
  try {
    clip.currentTime = 0;
  } catch {
    /* ignore */
  }
  clip.muted = false;
  clip.volume = ui.musicMuted ? 0 : volume;
  void clip.play().catch(() => {});
  return clip;
}

function playClip(file: string, volume = 1) {
  const clip = makeClip(file);
  clip.volume = ui.musicMuted ? 0 : volume;
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
      ui.bigWinDisplayMicro = Math.round(fromMicro + (toMicro - fromMicro) * easeOutCount(progress));
      ui.winMicro = ui.bigWinDisplayMicro;
      if (progress < 1) {
        requestAnimationFrame(tick);
        return;
      }
      ui.bigWinDisplayMicro = toMicro;
      ui.winMicro = toMicro;
      resolve();
    };
    ui.bigWinDisplayMicro = fromMicro;
    ui.winMicro = fromMicro;
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

/** Mute the lounge bed and start bzzz as soon as winning symbols sheen. */
export function beginBigWinIntro() {
  if (introActive) return;
  introActive = true;
  ui.bigWinIntro = true;
  duckMusicBed();
  playClip("bzzz.mp3");
  void warmStageClips();
  startFinished = (async () => {
    await waitForTimeout(BZZZ_TO_START_MS);
    if (!introActive) return;
    const start = playClip("start.mp3");
    await waitForClipEnd(start.clip, start.playing, START_FALLBACK_MS);
  })();
}

function finishBigWinAudio() {
  stopClips();
  introActive = false;
  ui.bigWinIntro = false;
  startFinished = Promise.resolve();
  resetOverlay();
  restoreMusicBed();
}

export async function playBigWin(micro: number) {
  const stages = stagesForWin(micro, ui.betMicro);
  if (!stages.length) return;

  beginBigWinIntro();

  try {
    await startFinished;
    if (!introActive) return;

    const first = startArmed(stages[0].file);
    const startedAt = performance.now();
    ui.bigWinOpen = true;
    ui.bigWinExplode = false;
    ui.bigWinOutgoingLeft = "";
    ui.bigWinOutgoingRight = "";

    let current = first;
    for (let index = 0; index < stages.length; index += 1) {
      const stage = stages[index];
      if (index > 0) {
        const wait = startedAt + index * STAGE_MS - performance.now();
        if (wait > 0) await waitForTimeout(wait);
        if (!introActive) return;
        const next = startArmed(stage.file);
        current.pause();
        current = next;
      }
      showStageTitle(stage.left, stage.right);
      const remain = startedAt + (index + 1) * STAGE_MS - performance.now();
      await countStage(stage.fromMicro, stage.toMicro, Math.max(16, remain));
    }
    current.pause();

    ui.bigWinExplode = true;
    const end = startArmed("end.mp3");
    await Promise.all([
      waitForClipEnd(end, Promise.resolve(!end.error), END_FALLBACK_MS),
      waitForTimeout(EXPLODE_MS),
    ]);
  } finally {
    finishBigWinAudio();
  }
}
