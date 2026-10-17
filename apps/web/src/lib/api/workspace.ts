import type { CustodioApi, WorkspaceCreated } from "./client";

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

export async function ensureWorkspace(
  api: Pick<CustodioApi, "createWorkspace">,
  store: WorkspaceStore,
): Promise<string> {
  const existing = store.read();
  if (existing) return existing;
  const created = await api.createWorkspace("demo");
  store.write(created);
  return created.workspace_id;
}
