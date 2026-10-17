import type { CustodioApi } from "./client";
import { createLiveClient } from "./live-client";
import { createMockClient } from "./mock/mock-client";
import { browserWorkspaceStore, ensureWorkspace } from "./workspace";

export type ApiMode = "mock" | "live";

export function apiModeFrom(value: string | undefined): ApiMode {
  return value === "mock" ? "mock" : "live";
}

export const API_MODE: ApiMode = apiModeFrom(process.env.NEXT_PUBLIC_API_MODE);

function createBrowserLiveClient(): CustodioApi {
  let pending: Promise<string> | null = null;
  const client: CustodioApi = createLiveClient({
    fetch: (...args) => fetch(...args),
    workspaceId: () => {
      pending ??= ensureWorkspace(client, browserWorkspaceStore).catch((error: unknown) => {
        pending = null;
        throw error;
      });
      return pending;
    },
  });
  return client;
}

export function createSessionClient(mode: ApiMode): CustodioApi {
  return mode === "mock" ? createMockClient() : createBrowserLiveClient();
}
