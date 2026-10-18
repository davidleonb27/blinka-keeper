import type { CustodioApi, WorkspaceCreated, WorkspaceMode } from "./client";

export const WORKSPACE_COOKIE = "custodio_ws";
const API_KEY_STORAGE = "custodio_api_key";
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

export interface WorkspaceStore {
  read(): string | null;
  readApiKey(): string | null;
  write(workspace: WorkspaceCreated): void;
}

export function readWorkspaceCookie(cookieHeader: string): string | null {
  for (const pair of cookieHeader.split(";")) {
    const [name, ...rest] = pair.trim().split("=");
    if (name === WORKSPACE_COOKIE) return decodeURIComponent(rest.join("=")) || null;
  }
  return null;
}

function localStorageOrNull(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The workspace id travels in a cookie; the API key stays in this browser only. */
export const browserWorkspaceStore: WorkspaceStore = {
  read: () => (typeof document === "undefined" ? null : readWorkspaceCookie(document.cookie)),
  readApiKey: () => localStorageOrNull()?.getItem(API_KEY_STORAGE) ?? null,
  write: ({ workspace_id, api_key }) => {
    document.cookie = `${WORKSPACE_COOKIE}=${encodeURIComponent(workspace_id)}; Path=/; Max-Age=${ONE_YEAR_SECONDS}; SameSite=Lax`;
    localStorageOrNull()?.setItem(API_KEY_STORAGE, api_key);
  },
};

// The blank workspace this tab made for a visitor who arrived to set up a company: the onboarding sets the company
// up in it instead of making a second one. In sessionStorage, so a reload in the middle of the set-up keeps it.
const FRESH_BLANK_STORAGE = "custodio_fresh_blank";

function sessionStorageOrNull(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function isFreshBlank(workspaceId: string): boolean {
  return sessionStorageOrNull()?.getItem(FRESH_BLANK_STORAGE) === workspaceId;
}

/** Once the company is set up in a fresh blank workspace, a new onboarding gets a workspace of its own. */
export function forgetFreshBlank(workspaceId: string): void {
  if (isFreshBlank(workspaceId)) sessionStorageOrNull()?.removeItem(FRESH_BLANK_STORAGE);
}

export async function ensureWorkspace(
  api: Pick<CustodioApi, "createWorkspace">,
  store: WorkspaceStore,
  mode: WorkspaceMode = "demo",
): Promise<string> {
  const existing = store.read();
  if (existing) return existing;
  const created = await api.createWorkspace(mode);
  store.write(created);
  if (mode === "blank") sessionStorageOrNull()?.setItem(FRESH_BLANK_STORAGE, created.workspace_id);
  return created.workspace_id;
}

/** A new demo workspace in place of one the API no longer has, unless another call already replaced it. */
export async function renewWorkspace(
  api: Pick<CustodioApi, "createWorkspace">,
  store: WorkspaceStore,
  stale: string,
): Promise<string> {
  const current = store.read();
  if (current && current !== stale) return current;
  const created = await api.createWorkspace("demo");
  store.write(created);
  return created.workspace_id;
}
