import { ui } from "./ui.svelte";

type Bed = "base" | "bonus";

const VOLUME = 0.34;
const FADE_MS = 720;

let base: HTMLAudioElement | null = null;
let bonus: HTMLAudioElement | null = null;
let unlocked = false;
let current: Bed = "base";
let fadeFrame = 0;

function trackUrl(file: string) {
  return `${import.meta.env.BASE_URL}audio/${file}`;
}

function makeLoop(file: string) {
  const audio = new Audio(trackUrl(file));
  audio.loop = true;
  audio.preload = "auto";
  audio.volume = 0;
  return audio;
}

function readMuted() {
  try {
    return window.localStorage.getItem("sunset-stereo-music") === "off";
  } catch {
    return false;
  }
}

function writeMuted(muted: boolean) {
  try {
    window.localStorage.setItem("sunset-stereo-music", muted ? "off" : "on");
  } catch {
    /* ignore */
  }
}

function cancelFade() {
  if (fadeFrame) cancelAnimationFrame(fadeFrame);
  fadeFrame = 0;
}

function fadeTo(target: HTMLAudioElement, next: number, ms = FADE_MS) {
  const from = target.volume;
  const started = performance.now();
  cancelFade();
  return new Promise<void>((resolve) => {
    const tick = (now: number) => {
      const u = Math.min((now - started) / ms, 1);
      target.volume = from + (next - from) * u;
      if (u < 1) {
        fadeFrame = requestAnimationFrame(tick);
        return;
      }
      fadeFrame = 0;
      target.volume = next;
      resolve();
    };
    fadeFrame = requestAnimationFrame(tick);
  });
}

export function bootMusic() {
  if (base && bonus) return;
  ui.musicMuted = readMuted();
  base = makeLoop("golden-hour-lounge.mp3");
  bonus = makeLoop("sunset-bonus-loop.mp3");
}

export async function unlockMusic() {
  bootMusic();
  if (!base || !bonus) return;
  unlocked = true;
  const bed = current === "bonus" ? bonus : base;
  const other = current === "bonus" ? base : bonus;
  other.pause();
  other.volume = 0;
  if (ui.musicMuted) {
    bed.pause();
    bed.volume = 0;
    return;
  }
  try {
    bed.volume = 0;
    await bed.play();
    await fadeTo(bed, VOLUME);
  } catch {
    unlocked = false;
  }
}

export async function setMusicBed(bed: Bed) {
  current = bed;
  if (!unlocked || !base || !bonus || ui.musicMuted) return;
  const next = bed === "bonus" ? bonus : base;
  const prev = bed === "bonus" ? base : bonus;
  if (!next.paused && prev.paused) return;
  try {
    next.volume = 0;
    await next.play();
    await Promise.all([fadeTo(next, VOLUME), fadeTo(prev, 0)]);
    if (current === bed) {
      prev.pause();
      prev.currentTime = 0;
    }
  } catch {
    /* autoplay still blocked */
  }
}

export async function toggleMusicMute() {
  bootMusic();
  ui.musicMuted = !ui.musicMuted;
  writeMuted(ui.musicMuted);
  if (!base || !bonus) return;
  if (ui.musicMuted) {
    cancelFade();
    base.pause();
    bonus.pause();
    base.volume = 0;
    bonus.volume = 0;
    return;
  }
  if (!unlocked) {
    await unlockMusic();
    return;
  }
  await setMusicBed(current);
}

export function musicBedFromUi() {
  return ui.feature || ui.bonusIntroOpen ? "bonus" : "base";
}
