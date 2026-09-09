import { ui } from "./ui.svelte";

type Bed = "base" | "bonus";

const VOLUME = 0.34;
const FADE_MS = 720;

let base: HTMLAudioElement | null = null;
let bonus: HTMLAudioElement | null = null;
let unlocked = false;
let current: Bed = "base";
let fadeFrame = 0;
let listening = false;

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

function activeTrack() {
  return current === "bonus" ? bonus : base;
}

function idleTrack() {
  return current === "bonus" ? base : bonus;
}

function isPlaying(audio: HTMLAudioElement | null) {
  return Boolean(audio && !audio.paused && !audio.ended);
}

export function bootMusic() {
  if (base && bonus) return;
  ui.musicMuted = readMuted();
  base = makeLoop("golden-hour-lounge.mp3");
  bonus = makeLoop("sunset-bonus-loop.mp3");
}

/** Call from a click/tap/key handler. play() is fired in this turn, not after await. */
export function unlockMusic() {
  bootMusic();
  if (!base || !bonus || ui.musicMuted) return;
  const active = activeTrack();
  const idle = idleTrack();
  if (!active || !idle) return;

  if (!isPlaying(active)) {
    active.volume = active.volume > 0 ? active.volume : 0;
    void active.play().then(() => {
      unlocked = true;
      if (!ui.musicMuted && active.volume < VOLUME) void fadeTo(active, VOLUME);
    }).catch(() => {
      unlocked = false;
    });
  } else {
    unlocked = true;
  }

  if (idle.paused) {
    idle.volume = 0;
    void idle.play().then(() => {
      if (idle !== activeTrack()) {
        idle.pause();
        idle.currentTime = 0;
      }
    }).catch(() => {
      /* second bed unlocks on the next gesture */
    });
  }
}

export async function setMusicBed(bed: Bed) {
  current = bed;
  if (!base || !bonus || ui.musicMuted) return;
  if (!unlocked && !isPlaying(base) && !isPlaying(bonus)) return;
  const next = bed === "bonus" ? bonus : base;
  const prev = bed === "bonus" ? base : bonus;
  if (isPlaying(next) && prev.paused) return;
  try {
    if (next.paused) {
      next.volume = 0;
      await next.play();
    }
    unlocked = true;
    await Promise.all([fadeTo(next, VOLUME), fadeTo(prev, 0)]);
    if (current === bed && prev !== next) {
      prev.pause();
      prev.currentTime = 0;
    }
  } catch {
    unlocked = isPlaying(next);
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
  unlockMusic();
  await setMusicBed(current);
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
    if (unlocked || ui.musicMuted) return;
  };
  const onVisible = () => {
    if (document.hidden || ui.musicMuted) return;
    if (unlocked || isPlaying(base) || isPlaying(bonus)) unlockMusic();
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
