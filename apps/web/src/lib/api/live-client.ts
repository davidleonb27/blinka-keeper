import type { CustodioApi } from "./client";
import type { RedTeamEvent } from "./contracts";
import { errorFromStatus, NetworkError, UnexpectedResponseError } from "./errors";
import { readSse } from "./sse";

export const API_BASE = "/api/v1";
export const WORKSPACE_HEADER = "X-Custodio-Workspace";

export interface LiveClientOptions {
  fetch: typeof fetch;
  workspaceId: () => string | null;
}

type Body = { json: unknown } | { form: FormData } | undefined;

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // An empty or non-JSON error body still maps to a typed error below.
  }
  return null;
}

export function createLiveClient({ fetch: fetchImpl, workspaceId }: LiveClientOptions): CustodioApi {
  function headersFor(body: Body): Headers {
    const headers = new Headers({ Accept: "application/json" });
    const id = workspaceId();
    if (id) headers.set(WORKSPACE_HEADER, id);
    if (body && "json" in body) headers.set("Content-Type", "application/json");
    return headers;
  }

  async function send(method: string, path: string, body?: Body): Promise<Response> {
    let response: Response;
    try {
      response = await fetchImpl(`${API_BASE}${path}`, {
        method,
        headers: headersFor(body),
        body: body && ("json" in body ? JSON.stringify(body.json) : body.form),
        credentials: "same-origin",
      });
    } catch {
      throw new NetworkError();
    }
    if (!response.ok) throw errorFromStatus(response.status, await readDetail(response));
    return response;
  }

  async function request<T>(method: string, path: string, body?: Body): Promise<T> {
    const response = await send(method, path, body);
    return (await response.json()) as T;
  }

  const get = <T>(path: string) => request<T>("GET", path);
  const post = <T>(path: string, json?: unknown) =>
    request<T>("POST", path, json === undefined ? undefined : { json });

  return {
    health: () => get("/health"),
    createWorkspace: (mode) => post("/workspaces", { mode }),
    getWorkspace: () => get("/workspaces/current"),
    listDecisions: () => get("/decisions"),
    getDecision: (id) => get(`/decisions/${encodeURIComponent(id)}`),
    approveDecision: (id, input) => post(`/decisions/${encodeURIComponent(id)}/approve`, input),
    rejectDecision: (id, input) => post(`/decisions/${encodeURIComponent(id)}/reject`, input),
    getPolicy: () => get("/policy"),
    compilePolicy: (text) => post("/policy/compile", { text }),
    applyPolicy: (policy) => request("PUT", "/policy", { json: policy }),
    getLedger: () => get("/ledger"),
    verifyLedger: () => get("/ledger/verify"),
    tamperDemo: () => post("/ledger/tamper-demo"),
    getChallengeStats: () => get("/challenge/stats"),
    submitChallengeAttempt: (input) => post("/challenge/attempts", input),
    proposeProfile: (input) => post("/onboarding/profile", input),
    completeOnboarding: (input) => post("/onboarding/complete", input),
    importSuppliers: (file) => {
      const form = new FormData();
      form.append("file", file);
      return request("POST", "/onboarding/suppliers", { form });
    },
    runRedTeam: async (input, onEvent, signal) => {
      const response = await send("POST", "/redteam/runs", { json: input });
      if (!response.body) throw new UnexpectedResponseError(response.status);
      if (signal?.aborted) return;
      await readSse(response.body, (message) => onEvent(JSON.parse(message.data) as RedTeamEvent));
    },
  };
}
