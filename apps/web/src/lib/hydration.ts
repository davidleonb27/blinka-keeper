import { useSyncExternalStore } from "react";

const noop = () => () => {};

/**
 * False while React hydrates (it reads the server snapshot) and true from the next render on. A hydration render must
 * match the server's HTML, and the server never knows the browser's theme, storage or the visitor's data.
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(noop, () => true, () => false);
}
