// A tab opened before a deploy asks for code the new deploy no longer serves. Reloading once fetches the new code;
// the session flag keeps a real, repeatable failure from turning into a reload loop.
const STALE_PATTERNS = [
  /ChunkLoadError/i,
  /Loading (CSS )?chunk [\w-]+ failed/i,
  /Failed to fetch dynamically imported module/i,
  /Importing a module script failed/i,
  /error loading dynamically imported module/i,
];
const RELOADED_KEY = "custodio_reloaded_after_deploy";

export function isStaleDeployError(error: unknown): boolean {
  const text = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  return STALE_PATTERNS.some((pattern) => pattern.test(text));
}

/** True when this error comes from a stale tab and the tab has not reloaded for it yet in this session. */
export function shouldReloadForNewDeploy(error: unknown): boolean {
  if (typeof window === "undefined" || !isStaleDeployError(error)) return false;
  try {
    return window.sessionStorage.getItem(RELOADED_KEY) === null;
  } catch {
    return false;
  }
}

export function reloadForNewDeploy(): void {
  try {
    window.sessionStorage.setItem(RELOADED_KEY, "1");
  } catch {
    return;
  }
  window.location.reload();
}
