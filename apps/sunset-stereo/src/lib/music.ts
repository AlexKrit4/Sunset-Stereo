import { ui } from "./ui.svelte";

type Bed = "base" | "bonus";

const VOLUME = 0.34;
const FADE_MS = 720;

let base: HTMLAudioElement | null = null;
let bonus: HTMLAudioElement | null = null;
let unlocked = false;
let current: Bed = "base";
let listening = false;
const fades = new WeakMap<HTMLAudioElement, number>();

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

function fadeVolume(target: HTMLAudioElement, next: number, ms = FADE_MS) {
  const prev = fades.get(target);
  if (prev) cancelAnimationFrame(prev);
  const from = target.volume;
  const safeNext = Math.min(Math.max(next, 0), 1);
  const started = performance.now();
  const tick = (now: number) => {
    const u = Math.min(Math.max((now - started) / ms, 0), 1);
    target.volume = Math.min(Math.max(from + (safeNext - from) * u, 0), 1);
    if (u < 1) {
      fades.set(target, requestAnimationFrame(tick));
      return;
    }
    fades.delete(target);
    target.volume = safeNext;
  };
  fades.set(target, requestAnimationFrame(tick));
}

function stopFades() {
  if (base) {
    const id = fades.get(base);
    if (id) cancelAnimationFrame(id);
    fades.delete(base);
  }
  if (bonus) {
    const id = fades.get(bonus);
    if (id) cancelAnimationFrame(id);
    fades.delete(bonus);
  }
}

function applyBedVolumes(immediate = false) {
  if (!base || !bonus) return;
  const next = current === "bonus" ? bonus : base;
  const prev = current === "bonus" ? base : bonus;
  if (ui.musicMuted) {
    next.volume = 0;
    prev.volume = 0;
    return;
  }
  if (immediate) {
    next.volume = VOLUME;
    prev.volume = 0;
    return;
  }
  fadeVolume(next, VOLUME);
  fadeVolume(prev, 0);
}

function startBoth() {
  if (!base || !bonus || ui.musicMuted) return;
  void base.play().then(() => {
    unlocked = true;
  }).catch(() => {});
  void bonus.play().then(() => {
    unlocked = true;
  }).catch(() => {});
}

export function bootMusic() {
  if (base && bonus) return;
  ui.musicMuted = readMuted();
  base = makeLoop("golden-hour-lounge.mp3");
  bonus = makeLoop("sunset-bonus-loop.mp3");
}

/** Call from a click/tap/key handler. play() stays in this turn. */
export function unlockMusic() {
  bootMusic();
  if (!base || !bonus || ui.musicMuted) return;
  startBoth();
  applyBedVolumes(base.paused && bonus.paused);
}

export function setMusicBed(bed: Bed) {
  current = bed;
  if (!base || !bonus || ui.musicMuted) return;
  applyBedVolumes();
}

export function toggleMusicMute() {
  bootMusic();
  ui.musicMuted = !ui.musicMuted;
  writeMuted(ui.musicMuted);
  if (!base || !bonus) return;
  if (ui.musicMuted) {
    stopFades();
    base.pause();
    bonus.pause();
    base.volume = 0;
    bonus.volume = 0;
    return;
  }
  startBoth();
  applyBedVolumes(true);
}

export function musicBedFromUi() {
  return ui.feature || ui.bonusIntroOpen ? "bonus" : "base";
}

export function bindMusicUnlock() {
  bootMusic();
  if (listening) return () => {};
  listening = true;
  const onGesture = () => {
    unlockMusic();
  };
  const onVisible = () => {
    if (document.hidden || ui.musicMuted) return;
    unlockMusic();
  };
  window.addEventListener("pointerdown", onGesture);
  window.addEventListener("click", onGesture);
  window.addEventListener("touchstart", onGesture, { passive: true });
  window.addEventListener("keydown", onGesture);
  document.addEventListener("visibilitychange", onVisible);
  return () => {
    listening = false;
    window.removeEventListener("pointerdown", onGesture);
    window.removeEventListener("click", onGesture);
    window.removeEventListener("touchstart", onGesture);
    window.removeEventListener("keydown", onGesture);
    document.removeEventListener("visibilitychange", onVisible);
  };
}
