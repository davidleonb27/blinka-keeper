import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CustodioApi, StripeProof } from "@/lib/api/client";
import { NetworkError } from "@/lib/api/errors";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { StripeProofBlock } from "./stripe-proof";

const TRANSFER_ID = "tr_1Qx7Custodio";
const VERIFIED: StripeProof = {
  invoice_id: "F-001",
  status: "verified",
  message: null,
  checked_at: new Date().toISOString(),
  transfer: {
    id: TRANSFER_ID,
    amount: 1200.5,
    currency: "usd",
    destination: "acct_andes",
    created: "2026-10-17T15:00:00Z",
    livemode: false,
    state: "paid",
    amount_reversed: 0,
    balance_transaction: { id: "txn_1", amount: -1200.5, fee: 0, net: -1200.5, status: "available", available_on: null },
  },
  checks: [
    { field: "amount", expected: "1200.50", actual: "1200.50", ok: true },
    { field: "currency", expected: "usd", actual: "usd", ok: true },
    { field: "beneficiary", expected: "acct_andes", actual: "acct_andes", ok: true },
    { field: "invoice", expected: "F-001", actual: "F-001", ok: true },
    { field: "livemode", expected: "false", actual: "false", ok: true },
    { field: "reversal", expected: "0.00", actual: "0.00", ok: true },
  ],
  dashboard_url: `https://dashboard.stripe.com/test/connect/transfers/${TRANSFER_ID}`,
  raw: { id: TRANSFER_ID, object: "transfer", livemode: false },
};

function apiAnswering(answer: () => Promise<StripeProof>): CustodioApi {
  return { ...createMockClient({ latencyMs: 0 }), getStripeProof: vi.fn(answer) };
}

describe("Pago en Stripe", () => {
  it("shows Stripe's live answer with every field checked against the acta, the raw JSON and the dashboard link", async () => {
    renderWithApi(<StripeProofBlock invoiceId="F-001" />, apiAnswering(async () => VERIFIED));

    const block = await screen.findByRole("region", { name: "Pago en Stripe" });
    expect(await within(block).findByText(/Stripe confirma el pago/)).toBeInTheDocument();
    expect(block).toHaveTextContent(/Verificado en Stripe hace \d+ s/);
    const checks = within(block).getByRole("list", { name: "Cotejo con el acta" });
    expect(within(checks).getAllByLabelText("coincide")).toHaveLength(6);
    expect(within(block).getByText("Respuesta de Stripe (JSON)")).toBeInTheDocument();
    expect(within(block).getByRole("link", { name: /Abrir en Stripe/ })).toHaveAttribute("href", VERIFIED.dashboard_url);
    expect(block).toHaveTextContent(/pide iniciar sesión/);
  });

  it("marks in red what Stripe says differently from the acta", async () => {
    const mismatch: StripeProof = {
      ...VERIFIED,
      status: "mismatch",
      checks: VERIFIED.checks.map((check) =>
        check.field === "amount" ? { ...check, actual: "1200.51", ok: false } : check,
      ),
    };
    renderWithApi(<StripeProofBlock invoiceId="F-001" />, apiAnswering(async () => mismatch));

    const block = await screen.findByRole("region", { name: "Pago en Stripe" });
    expect(await within(block).findByText(/no coincide con el acta/)).toBeInTheDocument();
    expect(within(block).getAllByLabelText("no coincide")).toHaveLength(1);
    expect(block).toHaveTextContent(/Acta: USD 1\.200,50 · Stripe: USD 1\.200,51/);
  });

  it("says plainly when Stripe does not have the transfer", async () => {
    const missing: StripeProof = { ...VERIFIED, status: "missing", transfer: null, checks: [], raw: null, dashboard_url: null, message: "Stripe no tiene ninguna transferencia con este id." };
    renderWithApi(<StripeProofBlock invoiceId="F-001" />, apiAnswering(async () => missing));

    expect(await screen.findByText(/no tiene ninguna transferencia/)).toBeInTheDocument();
    expect(screen.queryByText("Respuesta de Stripe (JSON)")).not.toBeInTheDocument();
  });

  it("never breaks the acta when Stripe or the API cannot be reached, and lets the person ask again", async () => {
    let calls = 0;
    const api = apiAnswering(async () => {
      calls += 1;
      if (calls === 1) throw new NetworkError();
      return VERIFIED;
    });
    renderWithApi(<StripeProofBlock invoiceId="F-001" />, api);

    expect(await screen.findByText("No se pudo consultar Stripe ahora.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Consultar de nuevo/ }));
    expect(await screen.findByText(/Stripe confirma el pago/)).toBeInTheDocument();
  });

  it("shows nothing for a payment that did not go through Stripe", async () => {
    const api = apiAnswering(async () => ({ ...VERIFIED, status: "not_applicable", checks: [], transfer: null, raw: null }));
    renderWithApi(<StripeProofBlock invoiceId="F-001" />, api);

    await vi.waitFor(() => expect(api.getStripeProof).toHaveBeenCalled());
    await vi.waitFor(() => expect(screen.queryByRole("region", { name: "Pago en Stripe" })).not.toBeInTheDocument());
  });
});
