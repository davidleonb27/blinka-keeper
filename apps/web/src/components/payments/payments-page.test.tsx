import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CustodioApi, PaymentsOverview } from "@/lib/api/client";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { saveFile } from "@/lib/download";
import { renderWithApi } from "@/test/render";
import { PaymentsPage } from "./payments-page";

vi.mock("@/lib/download", () => ({ saveFile: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/pagos",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const NOW = new Date().toISOString();
const BALANCED: PaymentsOverview = {
  rail: "stripe_test",
  base_currency: "USD",
  payments: [
    {
      invoice_id: "F-004",
      supplier_name: "Andes Code SAS",
      status: "paid_auto",
      amount: 1200.5,
      currency: "USD",
      amount_base: 1200.5,
      execution: {
        rail: "stripe_test",
        status: "executed",
        external_id: "tr_1",
        dashboard_url: "https://dashboard.stripe.com/test/connect/transfers/tr_1",
        executed_at: NOW,
        error: null,
      },
    },
  ],
  stripe: {
    status: "balanced",
    message: null,
    checked_at: NOW,
    complete: true,
    lines: [
      {
        kind: "matched",
        invoice_id: "F-004",
        supplier_name: "Andes Code SAS",
        recorded_amount: 1200.5,
        stripe_amount: 1200.5,
        transfer_id: "tr_1",
        dashboard_url: "https://dashboard.stripe.com/test/connect/transfers/tr_1",
      },
    ],
    recorded_total: 1200.5,
    stripe_total: 1200.5,
    difference: 0,
  },
  exportable: 3,
};

const OFF: PaymentsOverview = {
  ...BALANCED,
  stripe: {
    ...BALANCED.stripe,
    status: "differences",
    lines: [
      ...BALANCED.stripe.lines,
      {
        kind: "missing_in_registry",
        invoice_id: "F-077",
        supplier_name: null,
        recorded_amount: null,
        stripe_amount: 42,
        transfer_id: "tr_stray",
        dashboard_url: "https://dashboard.stripe.com/test/connect/transfers/tr_stray",
      },
    ],
    stripe_total: 1242.5,
    difference: 42,
  },
};

function apiWith(overview: PaymentsOverview): CustodioApi {
  return {
    ...createMockClient({ latencyMs: 0 }),
    getPayments: vi.fn(async () => overview),
    downloadPain001: vi.fn(async () => new Blob(["<Document/>"], { type: "application/xml" })),
  };
}

describe("/pagos", () => {
  it("shows that Custodio's record and Stripe balance, with the totals", async () => {
    renderWithApi(<PaymentsPage />, apiWith(BALANCED));

    const match = await screen.findByRole("region", { name: "Registro de Custodio ↔ Stripe" });
    expect(match).toHaveTextContent(/Cuadra: 1 pagos del registro, 1 transferencias en Stripe/);
    expect(match).toHaveTextContent(/Consultado en Stripe hace \d+ s/);
    expect(within(match).getByText("Diferencia").parentElement).toHaveTextContent("USD 0,00");
    const payments = screen.getByRole("region", { name: "Pagos del espacio" });
    expect(within(payments).getByRole("link", { name: "tr_1" })).toHaveAttribute("href", BALANCED.payments[0].execution?.dashboard_url);
  });

  it("marks a transfer Custodio never recorded and the difference in red", async () => {
    renderWithApi(<PaymentsPage />, apiWith(OFF));

    const match = await screen.findByRole("region", { name: "Registro de Custodio ↔ Stripe" });
    expect(match).toHaveTextContent(/No cuadra: 1 diferencia/);
    const stray = within(match).getByText("No está en el registro").closest("li");
    expect(stray).toHaveClass("bg-crit-weak");
    expect(stray).toHaveTextContent("tr_stray");
    expect(within(match).getByText("Diferencia").parentElement).toHaveClass("border-crit");
  });

  it("downloads the pain.001 file for Blinka", async () => {
    const api = apiWith(BALANCED);
    renderWithApi(<PaymentsPage />, api);

    const card = await screen.findByRole("region", { name: "Archivo para Blinka" });
    expect(card).toHaveTextContent("Listo para que Blinka lo pague");
    expect(card).toHaveTextContent("pain.001.001.09");
    await userEvent.click(within(card).getByRole("button", { name: /Descargar pain\.001/ }));
    expect(api.downloadPain001).toHaveBeenCalledOnce();
    expect(saveFile).toHaveBeenCalledWith(expect.any(Blob), "custodio-pain.001.001.09.xml");
  });

  it("keeps the payments on screen when Stripe cannot be asked", async () => {
    const down: PaymentsOverview = {
      ...BALANCED,
      stripe: { ...BALANCED.stripe, status: "unavailable", lines: [], message: "No se pudo consultar Stripe ahora." },
    };
    renderWithApi(<PaymentsPage />, apiWith(down));

    expect(await screen.findByText("No se pudo consultar Stripe ahora.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Pagos del espacio" })).toHaveTextContent("Andes Code SAS");
  });
});
