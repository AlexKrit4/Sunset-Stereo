export function createEventEmitter() {
  const listeners = new Map();

  function on(type, handler) {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type).add(handler);
    return () => listeners.get(type)?.delete(handler);
  }

  async function broadcast(event) {
    const handlers = listeners.get(event.type);
    if (!handlers) return;
    await Promise.all([...handlers].map((handler) => handler(event)));
  }

  return { on, broadcast };
}

export function createPlayBookUtils(handlerMap, emitter) {
  async function playBookEvent(bookEvent, context = {}) {
    const handler = handlerMap[bookEvent.type];
    if (!handler) {
      console.warn(`No handler for bookEvent ${bookEvent.type}`);
      return;
    }
    await handler(bookEvent, context);
  }

  async function playBookEvents(bookEvents, context = {}) {
    for (const bookEvent of bookEvents) {
      await playBookEvent(bookEvent, context);
      if (context.skipRemaining) break;
    }
  }

  return { playBookEvent, playBookEvents, emitter };
}

export function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
