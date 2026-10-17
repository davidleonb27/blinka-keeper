import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { INITIAL_ANSWERS, onboardingRequest } from "@/components/onboarding/state";
import { ApiProvider } from "@/components/providers/api-provider";
import { makeQueryClient } from "@/components/providers/providers";
import type { CustodioApi, WorkspaceCreated } from "./client";
import { InvalidRequestError } from "./errors";
import { useCompleteOnboarding } from "./hooks";
import { createMockClient } from "./mock/mock-client";

const VISITOR: WorkspaceCreated = { workspace_id: "ws_visitor", api_key: "cus_visitor" };
const NEW_COMPANY: WorkspaceCreated = { workspace_id: "ws_company", api_key: "cus_company" };

function memoryStore(initial: WorkspaceCreated) {
  let current = initial;
  return {
    read: () => current.workspace_id,
    readApiKey: () => current.api_key,
    write: vi.fn((next: WorkspaceCreated) => {
      current = next;
    }),
    current: () => current,
  };
}

function apiCreating(created: WorkspaceCreated): CustodioApi {
  const api = createMockClient({ latencyMs: 0 });
  vi.spyOn(api, "createWorkspace").mockResolvedValue(created);
  return api;
}

function completeWith(api: CustodioApi, store: ReturnType<typeof memoryStore>) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={makeQueryClient()}>
      <ApiProvider client={api} mode="mock">
        {children}
      </ApiProvider>
    </QueryClientProvider>
  );
  return renderHook(() => useCompleteOnboarding(store), { wrapper }).result;
}

describe("useCompleteOnboarding", () => {
  it("sets the new company up in a blank workspace of its own and keeps the browser there", async () => {
    const api = apiCreating(NEW_COMPANY);
    const store = memoryStore(VISITOR);
    const complete = completeWith(api, store);

    await act(() => complete.current.mutateAsync(onboardingRequest(INITIAL_ANSWERS)));

    expect(api.createWorkspace).toHaveBeenCalledWith("blank");
    expect(store.current()).toEqual(NEW_COMPANY);
  });

  it("brings the browser back to the workspace it had when the API refuses the company", async () => {
    const api = apiCreating(NEW_COMPANY);
    vi.spyOn(api, "completeOnboarding").mockRejectedValue(new InvalidRequestError(null, 422));
    const store = memoryStore(VISITOR);
    const complete = completeWith(api, store);

    await act(() => complete.current.mutateAsync(onboardingRequest(INITIAL_ANSWERS)).catch(() => undefined));

    expect(store.current()).toEqual(VISITOR);
  });
});
