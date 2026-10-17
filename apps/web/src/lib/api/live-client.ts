import type {
  ApiPath,
  ChallengeForm,
  CustodioApi,
  FormOf,
  JsonBodyOf,
  Method,
  PathParamsOf,
  ResponseOf,
} from "./client";
import type { RedTeamEvent } from "./contracts";
import { errorFromStatus, NetworkError, UnexpectedResponseError } from "./errors";
import { readSse } from "./sse";

export const API_BASE = "/api/v1";
const WORKSPACE_HEADER = "X-Custodio-Workspace";
const PATH_PARAM = /\{(\w+)\}/g;

export interface LiveClientOptions {
  fetch: typeof fetch;
  /** Resolves the visitor's workspace; may create it on first use. Never called for /workspaces. */
  workspaceId: () => Promise<string | null> | string | null;
}

interface CallOptions<P extends ApiPath, M extends Method> {
  params?: PathParamsOf<P, M>;
  json?: JsonBodyOf<P, M>;
  form?: FormData;
  scoped?: boolean;
  signal?: AbortSignal;
}

type FormFields<F> = { [K in keyof F]?: string | File | null };

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

function urlFor(path: string, params: unknown): string {
  const values = (params ?? {}) as Record<string, string>;
  return path.replace(PATH_PARAM, (_, name: string) => encodeURIComponent(values[name] ?? ""));
}

/** Multipart fields named after the route's OpenAPI body, so a renamed field fails tsc. */
function formOf<F>(fields: FormFields<F>): FormData {
  const form = new FormData();
  for (const [name, value] of Object.entries(fields)) {
    if (value instanceof File || (typeof value === "string" && value)) form.append(name, value);
  }
  return form;
}

export function createLiveClient({ fetch: fetchImpl, workspaceId }: LiveClientOptions): CustodioApi {
  async function headersFor(json: boolean, scoped: boolean): Promise<Headers> {
    const headers = new Headers({ Accept: "application/json" });
    const id = scoped ? await workspaceId() : null;
    if (id) headers.set(WORKSPACE_HEADER, id);
    if (json) headers.set("Content-Type", "application/json");
    return headers;
  }

  async function send<P extends ApiPath, M extends Method>(
    method: M,
    path: P,
    { params, json, form, scoped = true, signal }: CallOptions<P, M> = {},
  ): Promise<Response> {
    const headers = await headersFor(json !== undefined, scoped);
    let response: Response;
    try {
      response = await fetchImpl(urlFor(path, params), {
        method: method.toUpperCase(),
        headers,
        body: json !== undefined ? JSON.stringify(json) : form,
        credentials: "same-origin",
        signal,
      });
    } catch {
      throw new NetworkError();
    }
    if (!response.ok) throw errorFromStatus(response.status, await readDetail(response));
    return response;
  }

  async function call<P extends ApiPath, M extends Method>(
    method: M,
    path: P,
    options?: CallOptions<P, M>,
  ): Promise<ResponseOf<P, M>> {
    const response = await send(method, path, options);
    return (await response.json()) as ResponseOf<P, M>;
  }

  return {
    health: () => call("get", "/api/v1/health", { scoped: false }),
    createWorkspace: (mode) => call("post", "/api/v1/workspaces", { json: { mode }, scoped: false }),
    getWorkspace: () => call("get", "/api/v1/workspaces/current"),
    processInvoices: () => call("post", "/api/v1/invoices/process"),
    listDecisions: () => call("get", "/api/v1/decisions"),
    getDecision: (id) => call("get", "/api/v1/decisions/{invoice_id}", { params: { invoice_id: id } }),
    approveDecision: (id, input) =>
      call("post", "/api/v1/decisions/{invoice_id}/approve", { params: { invoice_id: id }, json: input }),
    rejectDecision: (id, input) =>
      call("post", "/api/v1/decisions/{invoice_id}/reject", { params: { invoice_id: id }, json: input }),
    executePayment: (id) => call("post", "/api/v1/decisions/{invoice_id}/execute", { params: { invoice_id: id } }),
    getPolicy: () => call("get", "/api/v1/policy"),
    compilePolicy: (text, base) => call("post", "/api/v1/policy/compile", { json: { text, base: base ?? null } }),
    applyPolicy: (policy) => call("put", "/api/v1/policy", { json: policy }),
    getLedger: () => call("get", "/api/v1/ledger"),
    verifyLedger: () => call("get", "/api/v1/ledger/verify"),
    tamperDemo: () => call("post", "/api/v1/ledger/tamper-demo", { json: {} }),
    getChallengeStats: () => call("get", "/api/v1/challenge/stats", { scoped: false }),
    submitChallengeAttempt: ({ text, alias, file }) =>
      call("post", "/api/v1/challenge/attempts", {
        form: formOf<ChallengeForm>(file ? { file, alias } : { text, alias }),
        scoped: false,
      }),
    proposeProfile: (input) => call("post", "/api/v1/onboarding/profile", { json: { ...input, answers: {} } }),
    completeOnboarding: (input) => call("post", "/api/v1/onboarding/complete", { json: input }),
    importSuppliers: (file) =>
      call("post", "/api/v1/onboarding/suppliers", {
        form: formOf<FormOf<"/api/v1/onboarding/suppliers", "post">>({ file }),
      }),
    runRedTeam: async (input, onEvent, signal) => {
      const response = await send("post", "/api/v1/redteam/runs", { json: input, signal });
      if (!response.body) throw new UnexpectedResponseError(response.status);
      await readSse(response.body, (message) => onEvent(JSON.parse(message.data) as RedTeamEvent));
    },
  };
}
