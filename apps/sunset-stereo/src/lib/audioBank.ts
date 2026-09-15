const BASE = import.meta.env.BASE_URL;

export const AUDIO_PATHS = [
  "audio/golden-hour-lounge.mp3",
  "audio/sunset-bonus-loop.mp3",
  "audio/bigwin/bzzz.mp3",
  "audio/bigwin/start.mp3",
  "audio/bigwin/win1.mp3",
  "audio/bigwin/win2.mp3",
  "audio/bigwin/win3.mp3",
  "audio/bigwin/win4.mp3",
  "audio/bigwin/win5.mp3",
  "audio/bigwin/end.mp3",
];

const blobUrls = new Map<string, string>();

export function assetUrl(path: string) {
  const trimmed = path.replace(/^\.\//, "");
  return new URL(`${BASE}${trimmed}`, document.baseURI).href;
}

export function audioSrc(path: string) {
  return blobUrls.get(path) || assetUrl(path);
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

async function warmAudio(url: string) {
  const clip = new Audio();
  clip.preload = "auto";
  clip.src = url;
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
      try {
        const response = await fetch(assetUrl(file.path), { cache: "force-cache" });
        if (!response.ok) throw new Error(`${file.path} ${response.status}`);
        const buffer = await bufferFromResponse(response, (received, total) => {
          file.received = received;
          file.total = total;
          report();
        });
        const blob = new Blob([buffer], { type: "audio/mpeg" });
        const url = URL.createObjectURL(blob);
        blobUrls.set(file.path, url);
        await warmAudio(url);
        file.received = file.total || file.received;
        file.done = true;
        report();
      } catch {
        file.done = true;
        report();
      }
    }),
  );
  onProgress(1);
}
