import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { SupplierTrust, TrustOverview } from "@/lib/api/client";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { AutonomyPage } from "./autonomy-page";

const REVOKED = {
  seq: 41,
  at: "2026-11-23T22:00:00Z",
  kind: "trust_revoked" as const,
  invoice_id: "SIM-1123-CUM",
  rule_id: "R4",
  reason: "La factura pide pagar a Banco Pichincha 7741-0093.",
  summary: "En supervisión.",
  cap_before: 318.5,
  cap_after: 0,
  clean_streak: 0,
  hash: "ab".repeat(32),
};

const RAISED = { ...REVOKED, seq: 30, kind: "trust_raised" as const, rule_id: null, invoice_id: "SIM-1109-CUM", reason: "Ana Gómez aprobó el pago.", cap_before: 0, cap_after: 252.2, clean_streak: 3 };

function supplier(overrides: Partial<SupplierTrust>): SupplierTrust {
  return {
    beneficiary_id: "b10",
    supplier_name: "Cumulus Hosting LLC",
    has_history: true,
    cap: 0,
    clean_streak: 2,
    supervised: true,
    reason: "En supervisión tras una señal de riesgo.",
    clean_needed: 1,
    next_cap: 270,
    last_incident: REVOKED,
    timeline: [RAISED, REVOKED],
    ...overrides,
  };
}

const OVERVIEW: TrustOverview = {
  base_currency: "USD",
  autonomy_rate: 0.57,
  floor: 0,
  ceiling: 12000,
  policy_threshold: 5000,
  hard_ceiling: false,
  clean_payments_to_earn: 3,
  suppliers: [
    supplier({}),
    supplier({
      beneficiary_id: "b1",
      supplier_name: "Andes Code SAS",
      has_history: false,
      cap: 5000,
      supervised: false,
      reason: "Sin historial de confianza.",
      last_incident: null,
      timeline: [],
      next_cap: null,
    }),
  ],
  autonomy: [{ day: "2026-11-02", decisions: 1, decided_alone: 0, rate: 0 }],
};

function api() {
  const client = createMockClient({ latencyMs: 0 });
  vi.spyOn(client, "getTrust").mockResolvedValue(OVERVIEW);
  return client;
}

describe("AutonomyPage", () => {
  it("shows the global autonomy rate and each supplier's cap against the ceiling", async () => {
    renderWithApi(<AutonomyPage />, api());

    expect(await screen.findByText("57 %", { exact: false })).toBeInTheDocument();
    const cumulus = screen.getByRole("article", { name: /Cumulus Hosting LLC/ });
    expect(within(cumulus).getByText(/En supervisión/, { selector: "span" })).toBeInTheDocument();
    expect(within(cumulus).getByRole("meter", { name: /Tope de Cumulus Hosting LLC/ })).toBeInTheDocument();
    expect(within(cumulus).getByText(/Falta 1 pago limpio/)).toBeInTheDocument();
    const andes = screen.getByRole("article", { name: /Andes Code SAS/ });
    expect(within(andes).getByText("USD 5.000")).toBeInTheDocument();
  });

  it("lists the raises and revocations with a link to their ledger entry", async () => {
    renderWithApi(<AutonomyPage />, api());

    const cumulus = await screen.findByRole("article", { name: /Cumulus Hosting LLC/ });
    const revoked = within(cumulus).getByRole("link", { name: /Asiento #41/ });
    expect(revoked).toHaveAttribute("href", "/registro#asiento-41");
    expect(within(cumulus).getByText(/Confianza revocada · R4/)).toBeInTheDocument();
    expect(within(cumulus).getByText(/Confianza ganada/)).toBeInTheDocument();
  });

  it("plays the simulated month from the demo button", async () => {
    const client = api();
    const simulate = vi.spyOn(client, "simulateMonth").mockResolvedValue({
      created: true,
      seed: 1330,
      start: "2026-11-01",
      days: 30,
      invoices: 15,
      inflow_base: 27370.17,
      trust: OVERVIEW,
    });
    renderWithApi(<AutonomyPage />, client);

    await userEvent.click(await screen.findByRole("button", { name: /Simular 30 días/ }));

    expect(simulate).toHaveBeenCalledOnce();
    expect(await screen.findByText(/15 facturas/)).toBeInTheDocument();
    expect(screen.getByText(/semilla 1330/)).toBeInTheDocument();
  });

  it("leads with the simulation when no supplier has earned a cap yet", async () => {
    const client = createMockClient({ latencyMs: 0 });
    const untouched = { ...OVERVIEW, suppliers: OVERVIEW.suppliers.map((one) => ({ ...one, timeline: one.timeline.filter((step) => step.kind !== "trust_raised") })) };
    vi.spyOn(client, "getTrust").mockResolvedValue(untouched);
    renderWithApi(<AutonomyPage />, client);

    const prompt = await screen.findByRole("region", { name: "Simular un mes" });
    expect(within(prompt).getByRole("button", { name: /Simular 30 días/ })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /Simular 30 días/ })).toHaveLength(1);
  });

  it("lists suppliers that earn or can earn a cap before those in supervision", async () => {
    renderWithApi(<AutonomyPage />, api());

    const cards = await screen.findAllByRole("article", { name: /SAS|LLC/ });
    expect(cards.map((card) => card.getAttribute("aria-labelledby"))).toEqual(["confianza-b1", "confianza-b10"]);
  });
});
