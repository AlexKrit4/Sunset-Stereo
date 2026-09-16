import loungeUrl from "../assets/audio/golden-hour-lounge.mp3?url";
import bonusUrl from "../assets/audio/sunset-bonus-loop.mp3?url";
import bzzzUrl from "../assets/audio/bigwin/bzzz.mp3?url";
import startUrl from "../assets/audio/bigwin/start.mp3?url";
import win1Url from "../assets/audio/bigwin/win1.mp3?url";
import win2Url from "../assets/audio/bigwin/win2.mp3?url";
import win3Url from "../assets/audio/bigwin/win3.mp3?url";
import win4Url from "../assets/audio/bigwin/win4.mp3?url";
import win5Url from "../assets/audio/bigwin/win5.mp3?url";
import endUrl from "../assets/audio/bigwin/end.mp3?url";

const BASE = import.meta.env.BASE_URL;

const AUDIO_URLS: Record<string, string> = {
  "audio/golden-hour-lounge.mp3": loungeUrl,
  "audio/sunset-bonus-loop.mp3": bonusUrl,
  "audio/bigwin/bzzz.mp3": bzzzUrl,
  "audio/bigwin/start.mp3": startUrl,
  "audio/bigwin/win1.mp3": win1Url,
  "audio/bigwin/win2.mp3": win2Url,
  "audio/bigwin/win3.mp3": win3Url,
  "audio/bigwin/win4.mp3": win4Url,
  "audio/bigwin/win5.mp3": win5Url,
  "audio/bigwin/end.mp3": endUrl,
};

export const AUDIO_PATHS = Object.keys(AUDIO_URLS);

export function assetUrl(path: string) {
  if (/^(?:blob:|data:|https?:)/i.test(path)) return path;
  const trimmed = path.replace(/^\.\//, "");
  const imported = AUDIO_URLS[trimmed];
  const relative = imported || `${BASE}${trimmed}`;
  return new URL(relative, pageBase()).href;
}

export function audioSrc(path: string) {
  return assetUrl(path);
}

function pageBase() {
  const url = new URL(document.baseURI || document.location.href);
  url.search = "";
  url.hash = "";
  return url.href;
}

async function bufferFromResponse(
  response: Response,
  onBytes: (received: number, total: number) => void,
) {
  const total = Number(response.headers.get("content-length")) || 0;
  if (!response.body) {
    const buf = await response.arrayBuffer();
    onBytes(buf.byteLength, buf.byteLength);
    return buf;
  }
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (value) {
      chunks.push(value);
      received += value.byteLength;
      onBytes(received, total || received);
    }
  }
  const out = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return out.buffer;
}

function prepareClip(url: string) {
  const clip = new Audio();
  clip.preload = "auto";
  clip.playsInline = true;
  clip.setAttribute("playsinline", "true");
  clip.setAttribute("webkit-playsinline", "true");
  clip.src = url;
  return clip;
}

async function warmAudio(url: string) {
  const clip = prepareClip(url);
  await new Promise<void>((resolve) => {
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      resolve();
    };
    const timer = window.setTimeout(done, 20000);
    clip.addEventListener("canplaythrough", done, { once: true });
    clip.addEventListener("error", done, { once: true });
    if (clip.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA) done();
    else clip.load();
  });
}

async function cacheAudio(url: string, onBytes: (received: number, total: number) => void) {
  try {
    const response = await fetch(url, { cache: "force-cache", mode: "same-origin" });
    if (!response.ok) return;
    await bufferFromResponse(response, onBytes);
  } catch {
    /* Engine CSP may block fetch; the audio element still loads the same URL. */
  }
}

export async function preloadAudio(onProgress: (ratio: number) => void) {
  const files = AUDIO_PATHS.map((path) => ({
    path,
    received: 0,
    total: 0,
    done: false,
  }));

  const report = () => {
    const totals = files.map((file) => file.total);
    const known = totals.every((total) => total > 0);
    if (known) {
      const received = files.reduce((sum, file) => sum + file.received, 0);
      const total = files.reduce((sum, file) => sum + file.total, 0);
      onProgress(total ? received / total : 1);
      return;
    }
    const finished = files.filter((file) => file.done).length;
    onProgress(finished / files.length);
  };

  await Promise.all(
    files.map(async (file) => {
      const url = assetUrl(file.path);
      await cacheAudio(url, (received, total) => {
        file.received = received;
        file.total = total;
        report();
      });
      await warmAudio(url);
      file.received = file.total || file.received;
      file.done = true;
      report();
    }),
  );
  onProgress(1);
}
