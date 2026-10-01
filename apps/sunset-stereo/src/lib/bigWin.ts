import { duckMusicBed, restoreMusicBed } from "./music";
import { audioSrc } from "./audioBank";
import { ui } from "./ui.svelte";
import { waitForTimeout } from "../utils/waitForTimeout";
import {
  BIG_WIN_MULT,
  BIG_WIN_STAGES,
  bigWinHudBase,
  hudWinFromBigWin,
  isBigWin as isBigWinAt,
  stagesForWin as stagesForWinAt,
} from "./bigWinStages.js";

export { BIG_WIN_MULT, BIG_WIN_STAGES, bigWinHudBase, hudWinFromBigWin };

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
const BZZZ_FALLBACK_MS = 6000;
const MAXWIN_COUNT_MS = 16000;
const MAXWIN_LEAVE_MS = 1500;

const clips: HTMLAudioElement[] = [];
const armed = new Map<string, HTMLAudioElement>();
let introActive = false;
let startScheduled = false;
let startFinished: Promise<void> = Promise.resolve();
let bzzzClip: HTMLAudioElement | null = null;
let bzzzPlaying: Promise<boolean> = Promise.resolve(false);
let bzzzStartedAt = 0;
let skipRequested = false;
const skipWaiters = new Set<() => void>();

/** Click during Big Win: snap the current stage to its sum and move on. */
export function skipBigWinStage() {
  skipRequested = true;
  [...skipWaiters].forEach((done) => done());
}

function takeSkip() {
  const was = skipRequested;
  skipRequested = false;
  return was;
}

function skippableTimeout(ms: number) {
  return new Promise<void>((resolve) => {
    const timer = window.setTimeout(() => {
      skipWaiters.delete(done);
      resolve();
    }, ms);
    const done = () => {
      window.clearTimeout(timer);
      skipWaiters.delete(done);
      resolve();
    };
    skipWaiters.add(done);
  });
}

function audioUrl(file: string) {
  return audioSrc(file.startsWith("audio/") ? file : `audio/bigwin/${file}`);
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
      skipWaiters.delete(done);
      window.clearTimeout(timer);
      resolve();
    };
    skipWaiters.add(done);
    const timer = window.setTimeout(done, fallbackMs);
    clip.addEventListener("ended", done, { once: true });
    clip.addEventListener("error", done, { once: true });
    if (clip.ended || clip.error) done();
  });
}

function syncHud(displayMicro: number) {
  ui.bigWinDisplayMicro = displayMicro;
  ui.winMicro = hudWinFromBigWin(displayMicro, ui.bigWinHudBaseMicro);
}

function countStage(fromMicro: number, toMicro: number, ms: number) {
  takeSkip();
  if (toMicro === fromMicro) {
    syncHud(fromMicro);
    return waitForTimeout(ms);
  }
  return new Promise<void>((resolve) => {
    const started = performance.now();
    const tick = (now: number) => {
      if (!ui.bigWinOpen) {
        resolve();
        return;
      }
      const progress = skipRequested ? 1 : Math.min(1, (now - started) / ms);
      syncHud(Math.round(fromMicro + (toMicro - fromMicro) * easeOutCount(progress)));
      if (progress < 1) {
        requestAnimationFrame(tick);
        return;
      }
      takeSkip();
      syncHud(toMicro);
      resolve();
    };
    syncHud(fromMicro);
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
  ui.bigWinHudBaseMicro = 0;
}

/** Mute the lounge bed and start bzzz as soon as winning symbols sheen. */
export function beginBigWinIntro() {
  if (introActive) return;
  introActive = true;
  ui.bigWinIntro = true;
  duckMusicBed();
  const bzzz = playClip("bzzz.mp3");
  bzzzClip = bzzz.clip;
  bzzzPlaying = bzzz.playing;
  bzzzStartedAt = performance.now();
  void warmStageClips();
}

function scheduleStageStart() {
  if (startScheduled) return;
  startScheduled = true;
  startFinished = (async () => {
    await skippableTimeout(Math.max(0, BZZZ_TO_START_MS - (performance.now() - bzzzStartedAt)));
    if (!introActive || takeSkip()) return;
    const start = playClip("start.mp3");
    await waitForClipEnd(start.clip, start.playing, START_FALLBACK_MS);
    if (takeSkip()) start.clip.pause();
  })();
}

let maxWinContinueResolve: (() => void) | null = null;

/** Continue button on the Max Win scene. */
export function confirmMaxWin() {
  const resolve = maxWinContinueResolve;
  maxWinContinueResolve = null;
  resolve?.();
}

function countMaxWin(toMicro: number, ms: number) {
  return new Promise<void>((resolve) => {
    const started = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / ms);
      const shown = Math.round(toMicro * easeOutCount(progress));
      ui.maxWinDisplayMicro = shown;
      ui.winMicro = shown;
      if (progress < 1) {
        requestAnimationFrame(tick);
        return;
      }
      ui.maxWinDisplayMicro = toMicro;
      ui.winMicro = toMicro;
      resolve();
    };
    requestAnimationFrame(tick);
  });
}

/** Wincap: bzzz + sheen, then the fullscreen Max Win count scene. */
export async function playWincapBzzz(totalMicro: number) {
  await playMaxWin(totalMicro);
}

export async function playMaxWin(totalMicro: number) {
  beginBigWinIntro();
  if (bzzzClip) {
    await waitForClipEnd(bzzzClip, bzzzPlaying, BZZZ_FALLBACK_MS);
  }

  ui.maxWinOpen = true;
  ui.maxWinReady = false;
  ui.maxWinPulse = false;
  ui.maxWinLeaving = false;
  ui.maxWinDisplayMicro = 0;

  playClip("audio/maxwin/zmaxwin1.mp3");
  await countMaxWin(totalMicro, MAXWIN_COUNT_MS);

  const loop = makeClip("audio/maxwin/zmaxwin2.mp3");
  loop.loop = true;
  loop.volume = ui.musicMuted ? 0 : 1;
  void loop.play().catch(() => {});
  ui.maxWinReady = true;

  await new Promise<void>((resolve) => {
    maxWinContinueResolve = resolve;
  });

  stopClips();
  ui.maxWinPulse = true;
  const end = playClip("end.mp3");
  await Promise.all([
    waitForClipEnd(end.clip, end.playing, END_FALLBACK_MS),
    waitForTimeout(EXPLODE_MS),
  ]);

  ui.maxWinLeaving = true;
  await waitForTimeout(MAXWIN_LEAVE_MS);

  ui.maxWinOpen = false;
  ui.maxWinReady = false;
  ui.maxWinPulse = false;
  ui.maxWinLeaving = false;
  ui.maxWinDisplayMicro = 0;
  finishBigWinAudio();
}

function finishBigWinAudio() {
  stopClips();
  introActive = false;
  ui.bigWinIntro = false;
  startScheduled = false;
  startFinished = Promise.resolve();
  bzzzClip = null;
  bzzzPlaying = Promise.resolve(false);
  skipRequested = false;
  skipWaiters.clear();
  resetOverlay();
  restoreMusicBed();
}

export async function playBigWin(micro: number, hudBaseMicro = 0) {
  const base = Math.max(0, hudBaseMicro);
  ui.bigWinHudBaseMicro = base;
  const stages = stagesForWin(micro, ui.betMicro);
  if (!stages.length) {
    ui.winMicro = base + micro;
    return;
  }

  beginBigWinIntro();
  scheduleStageStart();

  try {
    await startFinished;
    if (!introActive) return;

    const first = startArmed(stages[0].file);
    syncHud(stages[0].fromMicro);
    ui.bigWinOpen = true;
    ui.bigWinExplode = false;
    ui.bigWinOutgoingLeft = "";
    ui.bigWinOutgoingRight = "";

    let current = first;
    for (let index = 0; index < stages.length; index += 1) {
      const stage = stages[index];
      if (index > 0) {
        if (!introActive) return;
        const next = startArmed(stage.file);
        current.pause();
        current = next;
      }
      showStageTitle(stage.left, stage.right);
      await countStage(stage.fromMicro, stage.toMicro, STAGE_MS);
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
