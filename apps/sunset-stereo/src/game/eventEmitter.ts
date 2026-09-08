import type { EmitterEvent } from "./types";

type Handler = (event: EmitterEvent) => void | Promise<void>;

export function createEventEmitter() {
  const listeners = new Map<string, Set<Handler>>();

  function on(type: EmitterEvent["type"], handler: Handler) {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type)!.add(handler);
    return () => listeners.get(type)?.delete(handler);
  }

  async function broadcast(event: EmitterEvent) {
    const handlers = listeners.get(event.type);
    if (!handlers) return;
    await Promise.all([...handlers].map((handler) => handler(event)));
  }

  return { on, broadcast };
}

export const eventEmitter = createEventEmitter();

export function wait(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });
}
