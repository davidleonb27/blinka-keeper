import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { ApiProvider } from "@/components/providers/api-provider";
import { makeQueryClient } from "@/components/providers/providers";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { CustodioApi } from "@/lib/api/client";
import { createMockClient } from "@/lib/api/mock/mock-client";

export function renderWithApi(ui: ReactElement, api: CustodioApi = createMockClient({ latencyMs: 0 })) {
  const queryClient = makeQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false } });
  return {
    api,
    ...render(
      <QueryClientProvider client={queryClient}>
        <ApiProvider client={api} mode="mock">
          <TooltipProvider>{ui}</TooltipProvider>
        </ApiProvider>
      </QueryClientProvider>,
    ),
  };
}
