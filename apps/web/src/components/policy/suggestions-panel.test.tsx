import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Suggestion } from "@/lib/api/client";
import { DEMO } from "@/lib/api/mock/dataset";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { SuggestionsPanel } from "./suggestions-panel";

const METRICS = { total: 3, paid_auto: 0, paid_human: 0, hold: 0, pending: 3, rejected: 0, autonomy_rate: 0, improper_payments: 0 };
const SUGGESTION: Suggestion = {
  id: "abc123",
  beneficiary_id: "b8",
  supplier_name: "Nube Austral SpA",
  rule_id: "R6",
  question:
    "Aprobaste 3 veces a Nube Austral SpA por pasar hasta 4,14 % por encima del acuerdo (USD 2.150); ¿subo la tolerancia de este proveedor a 5 %?",
  current_tolerance_pct: 2,
  proposed_tolerance_pct: 5,
  evidence: [
    {
      invoice_id: "H-NA-7712",
      amount: 2236,
      currency: "USD",
      deviation_pct: 4,
      approver: "Ana Gómez",
      approved_at: "2026-06-05T15:00:00Z",
      note: "Subió el plan de hosting",
    },
  ],
  changes: [],
  simulation: { before: METRICS, after: METRICS, changed: [] },
  policy_version: 1,
};

function apiWith(suggestions: Suggestion[]) {
  const api = createMockClient({ latencyMs: 0 });
  vi.spyOn(api, "listSuggestions").mockResolvedValue(suggestions);
  const accept = vi.spyOn(api, "acceptSuggestion").mockResolvedValue({ ...DEMO.policy, version: 2 });
  return { api, accept };
}

describe("SuggestionsPanel", () => {
  it("shows the suggestion in plain words with its evidence, and applies it only when accepted", async () => {
    const { api, accept } = apiWith([SUGGESTION]);
    renderWithApi(<SuggestionsPanel policy={DEMO.policy} />, api);

    expect(await screen.findByText(/Aprobaste 3 veces a Nube Austral SpA/)).toBeInTheDocument();
    expect(screen.getByText(/Subió el plan de hosting/)).toBeInTheDocument();
    expect(accept).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: /aplicar como versión 2/ }));

    expect(accept).toHaveBeenCalledWith("abc123", { approver: "Ana Gómez", expected_policy_version: 1 });
  });

  it("stays out of the way when there is nothing to suggest", async () => {
    const { api } = apiWith([]);
    renderWithApi(<SuggestionsPanel policy={DEMO.policy} />, api);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByRole("region", { name: "Blinka Keeper sugiere" })).not.toBeInTheDocument();
  });
});
