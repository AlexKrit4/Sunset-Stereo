import { bookEventHandlerMap } from "./bookEventHandlerMap.svelte";
import type { BookEvent, BookEventContext } from "./typesBookEvent";

export async function playBookEvent(bookEvent: BookEvent, context: BookEventContext) {
  const handler = bookEventHandlerMap[bookEvent.type] as
    | ((event: BookEvent, ctx: BookEventContext) => void | Promise<void>)
    | undefined;
  if (!handler) {
    console.warn(`No handler for bookEvent ${bookEvent.type}`);
    return;
  }
  await handler(bookEvent, context);
}

export async function playBookEvents(bookEvents: BookEvent[], context?: BookEventContext) {
  const ctx = context ?? { bookEvents };
  for (const bookEvent of bookEvents) {
    await playBookEvent(bookEvent, ctx);
  }
}
