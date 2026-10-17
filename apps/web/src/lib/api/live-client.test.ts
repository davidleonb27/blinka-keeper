import { describe, expect, it, vi } from "vitest";
import {
  NetworkError,
  NotFoundError,
  PayloadTooLargeError,
  RateLimitedError,
  ServiceUnavailableError,
} from "./errors";
import { createLiveClient } from "./live-client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function clientWith(fetchImpl: typeof fetch, workspaceId: string | null = "ws_123") {
  return createLiveClient({ fetch: fetchImpl, workspaceId: () => workspaceId });
}

describe("live client", () => {
  it("calls the relative /api/v1 path with the workspace header", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse(200, []));
    await clientWith(fetchMock).listDecisions();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/decisions");
    expect(new Headers(init?.headers).get("X-Custodio-Workspace")).toBe("ws_123");
  });

  it("omits the workspace header when there is no workspace yet", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      jsonResponse(200, { workspace_id: "ws_new", api_key: "ck_1" }),
    );
    await clientWith(fetchMock, null).createWorkspace("demo");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/workspaces");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({ mode: "demo" }));
    expect(new Headers(init?.headers).has("X-Custodio-Workspace")).toBe(false);
  });

  it("posts approvals to the decision route", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse(200, {}));
    await clientWith(fetchMock).approveDecision("F-020", { approver: "Ana Gómez" });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/decisions/F-020/approve");
    expect(init?.method).toBe("POST");
  });

  it("turns a 429 into a Spanish rate-limit error", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse(429, { detail: "rate" }));
    const error = await clientWith(fetchMock).getWorkspace().catch((e: unknown) => e);

    expect(error).toBeInstanceOf(RateLimitedError);
    expect((error as Error).message).toBe(
      "Vas muy rápido. Espera un minuto y vuelve a intentarlo.",
    );
  });

  it("keeps the honest message the API sends with a 503", async () => {
    const detail = "No pudimos leerla; queda para revisión humana.";
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse(503, { detail }));
    const error = await clientWith(fetchMock).getWorkspace().catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ServiceUnavailableError);
    expect((error as Error).message).toBe(detail);
  });

  it("explains a 503 without a body in Spanish", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response("", { status: 503 }));
    const error = await clientWith(fetchMock).getWorkspace().catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ServiceUnavailableError);
    expect((error as Error).message).toMatch(/no está disponible/);
  });

  it("maps 404 and 413 to their own errors", async () => {
    const notFound = vi.fn<typeof fetch>(async () => jsonResponse(404, { detail: "x" }));
    const tooLarge = vi.fn<typeof fetch>(async () => jsonResponse(413, { detail: "x" }));

    await expect(clientWith(notFound).getDecision("F-404")).rejects.toBeInstanceOf(NotFoundError);
    await expect(
      clientWith(tooLarge).importSuppliers(new File(["x"], "lista.csv")),
    ).rejects.toBeInstanceOf(PayloadTooLargeError);
  });

  it("reports a network failure without leaking the raw error", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => {
      throw new TypeError("Failed to fetch");
    });
    const error = await clientWith(fetchMock).getWorkspace().catch((e: unknown) => e);

    expect(error).toBeInstanceOf(NetworkError);
    expect((error as Error).message).toMatch(/No pudimos conectarnos/);
  });
});
