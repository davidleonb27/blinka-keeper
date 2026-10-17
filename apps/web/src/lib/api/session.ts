import type { CustodioApi } from "./client";
import { createLiveClient } from "./live-client";
import { createMockClient } from "./mock/mock-client";
import { browserWorkspaceStore, ensureWorkspace, renewWorkspace } from "./workspace";

export type ApiMode = "mock" | "live";

function apiModeFrom(value: string | undefined): ApiMode {
  return value === "mock" ? "mock" : "live";
}

export const API_MODE: ApiMode = apiModeFrom(process.env.NEXT_PUBLIC_API_MODE);

/** The page's queries run in parallel: they share one creation of the visitor's workspace instead of racing. */
function createBrowserLiveClient(): CustodioApi {
  let pending: Promise<string> | null = null;
  const once = (create: () => Promise<string>): Promise<string> =>
    (pending ??= create().finally(() => {
      pending = null;
    }));
  const client: CustodioApi = createLiveClient({
    fetch: (...args) => fetch(...args),
    workspaceId: () => browserWorkspaceStore.read() ?? once(() => ensureWorkspace(client, browserWorkspaceStore)),
    replaceWorkspace: (stale) => once(() => renewWorkspace(client, browserWorkspaceStore, stale)),
  });
  return client;
}

export function createSessionClient(mode: ApiMode): CustodioApi {
  return mode === "mock" ? createMockClient() : createBrowserLiveClient();
}
