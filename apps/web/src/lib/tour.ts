import { useSyncExternalStore } from "react";

/** The guided walk through the panel. Its state lives only in this browser: nothing reaches the API. */
export type TourStep = "decide" | "acta" | "rule" | "reconcile" | "verify" | "steal";

export interface TourState {
  done: readonly TourStep[];
  dismissed: boolean;
}

const STORAGE_KEY = "custodio_tour";
const CHANGED = "custodio-tour-changed";
const EMPTY: TourState = { done: [], dismissed: false };

let cachedRaw: string | null = null;
let cached: TourState = EMPTY;

function read(): TourState {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return cached; // private windows and blocked storage: the walk still works for this page view
  }
  if (raw === cachedRaw) return cached;
  cachedRaw = raw;
  cached = parse(raw);
  return cached;
}

function parse(raw: string | null): TourState {
  if (!raw) return EMPTY;
  try {
    const value = JSON.parse(raw) as Partial<TourState>;
    return { done: Array.isArray(value.done) ? value.done : [], dismissed: value.dismissed === true };
  } catch {
    return EMPTY;
  }
}

function write(next: TourState) {
  cached = next;
  try {
    cachedRaw = JSON.stringify(next);
    window.localStorage.setItem(STORAGE_KEY, cachedRaw);
  } catch {
    // kept in memory only
  }
  window.dispatchEvent(new Event(CHANGED));
}

export function markTourStep(step: TourStep) {
  if (typeof window === "undefined") return;
  const state = read();
  if (!state.done.includes(step)) write({ ...state, done: [...state.done, step] });
}

export function setTourDismissed(dismissed: boolean) {
  write({ ...read(), dismissed });
}

function subscribe(onChange: () => void) {
  window.addEventListener(CHANGED, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(CHANGED, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** The server and the hydration render see an empty walk; the browser's own state arrives right after. */
export function useTour(): TourState {
  return useSyncExternalStore(subscribe, read, () => EMPTY);
}
