type BookState = {
  id: number;
  events: unknown[];
  payoutMultiplier: number;
  criteria?: string;
};

type BookIndexEntry = { s: number; n: number };

const MODE_FILES: Record<string, string> = {
  base: "base",
  scatter: "scatter",
  bonus: "bonus",
  wildbonus: "wildbonus",
};

const indexes = new Map<string, BookIndexEntry[]>();

function poolFile(mode: string, ext: "idx.json" | "jsonl") {
  const name = MODE_FILES[mode] ?? "base";
  return new URL(`./vps/${name}.${ext}`, window.location.href).href;
}

async function loadIndex(mode: string): Promise<BookIndexEntry[]> {
  const key = MODE_FILES[mode] ?? "base";
  const cached = indexes.get(key);
  if (cached?.length) return cached;
  const res = await fetch(poolFile(mode, "idx.json"), { cache: "no-cache" });
  if (!res.ok) throw new Error(`VPS book index ${key} failed (${res.status}).`);
  const entries = (await res.json()) as BookIndexEntry[];
  if (!Array.isArray(entries) || !entries.length) throw new Error(`VPS book index ${key} is empty.`);
  indexes.set(key, entries);
  return entries;
}

function pickEntry(entries: BookIndexEntry[]) {
  return entries[Math.floor(Math.random() * entries.length)] ?? entries[0];
}

async function fetchSlice(mode: string, entry: BookIndexEntry) {
  const start = entry.s;
  const end = entry.s + entry.n - 1;
  const res = await fetch(poolFile(mode, "jsonl"), {
    headers: { Range: `bytes=${start}-${end}` },
    cache: "no-store",
  });
  if (!res.ok && res.status !== 206) {
    throw new Error(`VPS book ${mode} failed (${res.status}).`);
  }
  const text = (await res.text()).trim();
  if (!text) throw new Error(`VPS book ${mode} slice was empty.`);
  return JSON.parse(text.split("\n")[0] ?? text) as BookState;
}

export async function loadVpsBook(mode: string, fallback: BookState[]): Promise<BookState> {
  try {
    const entries = await loadIndex(mode);
    const book = await fetchSlice(mode, pickEntry(entries));
    if (!book?.events?.length) throw new Error("VPS book has no events.");
    return book;
  } catch (error) {
    if (!fallback.length) throw error;
    return fallback[Math.floor(Math.random() * fallback.length)] ?? fallback[0];
  }
}

export function randomDemoBook(pool: BookState[]) {
  if (!pool.length) throw new Error("No mock books.");
  return pool[Math.floor(Math.random() * pool.length)] ?? pool[0];
}
