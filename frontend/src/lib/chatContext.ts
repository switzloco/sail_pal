/**
 * Hand-off between a detail page and the chat page.
 *
 * sessionStorage rather than a query param: the frontend ships as a static
 * export, where `useSearchParams` needs its own Suspense boundary on every
 * consuming page. A key that survives one navigation is all this needs.
 */
export const CHAT_COMPONENT_KEY = "vessel_ops_chat_component";
export const CHAT_CREW_KEY = "vessel_ops_chat_crew";

export function handOffToChat(key: string, value: string) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(key, value);
}

/** Read a hand-off value once, clearing it so a later visit starts clean. */
export function consumeChatHandOff(key: string): string | null {
  if (typeof window === "undefined") return null;
  const value = sessionStorage.getItem(key);
  if (value) sessionStorage.removeItem(key);
  return value;
}
