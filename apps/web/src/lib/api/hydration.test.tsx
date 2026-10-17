import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { act } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { ApiProvider } from "@/components/providers/api-provider";
import { makeQueryClient } from "@/components/providers/providers";
import { useWorkspaceSummary } from "./hooks";
import { createMockClient } from "./mock/mock-client";

const LOADING = "Cargando…";

function CompanyName() {
  const summary = useWorkspaceSummary();
  return <p>{summary.data?.company_name ?? LOADING}</p>;
}

function app(queryClient: QueryClient) {
  return (
    <QueryClientProvider client={queryClient}>
      <ApiProvider client={createMockClient({ latencyMs: 0 })} mode="mock">
        <CompanyName />
      </ApiProvider>
    </QueryClientProvider>
  );
}

describe("data hooks during hydration", () => {
  it("render what the server rendered even when the data is already cached, then show it", async () => {
    // The server never has the visitor's data; the browser may, when another part of the page fetched it first.
    const serverHtml = renderToString(app(makeQueryClient()));
    const browserCache = makeQueryClient();
    browserCache.setQueryData(["workspace"], await createMockClient({ latencyMs: 0 }).getWorkspace());
    const container = document.createElement("div");
    container.innerHTML = serverHtml;
    const onRecoverableError = vi.fn();

    await act(async () => {
      hydrateRoot(container, app(browserCache), { onRecoverableError });
    });

    expect(serverHtml).toContain(LOADING);
    expect(onRecoverableError).not.toHaveBeenCalled();
    expect(container.textContent).toBe("Cobalto Labs, Inc.");
  });
});
