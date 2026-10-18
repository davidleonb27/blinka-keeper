import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CorrectionIssued, CorrectionOffer, CorrectionRequest, SupplierCorrectionView } from "@/lib/api/client";
import { InvalidRequestError } from "@/lib/api/errors";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { CorrectionPanel } from "./correction-panel";
import { waitingInvoices } from "./labels";
import { SupplierCorrection } from "./supplier-correction";

const ISSUE = {
  kind: "amount_unreadable" as const,
  rule_id: "R1",
  fields: ["amount" as const],
  problem: "El monto de la factura no se pudo leer con certeza.",
  expected: "USD 1.900, el monto acordado, escrito con claridad",
};

const OFFER: CorrectionOffer = {
  invoice_id: "F-039",
  offered: true,
  reason: null,
  issues: [ISSUE],
  blockers: [],
  still_for_a_person: [],
  confirmable_fields: ["amount"],
  next_round: 1,
  max_rounds: 2,
  open_request: null,
  history: [],
};

const REQUEST: CorrectionRequest = {
  id: "r1",
  invoice_id: "F-039",
  root_invoice_id: "F-039",
  round: 1,
  status: "open",
  issues: [ISSUE],
  message: "Hola, Valentina Ortiz: …",
  channels: ["link"],
  created_at: "2026-10-17T15:00:00Z",
  expires_at: "2026-10-24T15:00:00Z",
  submitted_at: null,
  corrected_invoice_id: null,
  outcome: null,
  alert: null,
};

const ISSUED: CorrectionIssued = {
  request: REQUEST,
  link: "https://custodio.test/proveedor/c/tok",
  message: "Hola, Valentina Ortiz:\nPuede corregirla aquí: https://custodio.test/proveedor/c/tok",
  whatsapp: "not_whatsapp",
};

const VIEW: SupplierCorrectionView = {
  company_name: "Cobalto Labs, Inc.",
  supplier_name: "Valentina Ortiz",
  reference: "VO-11",
  amount: 1900,
  currency: "USD",
  issues: [{ problem: ISSUE.problem, expected: ISSUE.expected, fields: ["amount"] }],
  fields: ["amount"],
  confirmable: true,
  round: 1,
  max_rounds: 2,
  expires_at: "2026-10-24T15:00:00Z",
  accepted_media_types: ["application/pdf", "image/jpeg"],
};

function api() {
  return createMockClient({ latencyMs: 0 });
}

describe("CorrectionPanel", () => {
  it("offers to ask the supplier and shows the message to copy", async () => {
    const client = api();
    vi.spyOn(client, "getCorrectionOffer").mockResolvedValue(OFFER);
    const ask = vi.spyOn(client, "requestCorrection").mockResolvedValue(ISSUED);
    renderWithApi(<CorrectionPanel invoiceId="F-039" cameByWhatsApp={false} />, client);

    expect(await screen.findByText(/no se pudo leer con certeza/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Pedir corrección al proveedor/ }));

    expect(ask).toHaveBeenCalledWith("F-039", { whatsapp: false });
    expect(await screen.findByDisplayValue(/proveedor\/c\/tok/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Copiar enlace/ })).toBeInTheDocument();
    expect(screen.getByText(/no llegó por WhatsApp/)).toBeInTheDocument();
  });

  it("says why a non-negotiable stop is not negotiated and offers nothing", async () => {
    const client = api();
    vi.spyOn(client, "getCorrectionOffer").mockResolvedValue({
      ...OFFER,
      offered: false,
      reason: "Tiene causas que no se negocian con el proveedor; las revisa una persona.",
      blockers: [{ kind: "account_changed", rule_id: "R4", reason: "La cuenta de la factura no es la registrada." }],
    });
    renderWithApi(<CorrectionPanel invoiceId="F-023" cameByWhatsApp={false} />, client);

    expect(await screen.findByText("No se negocia con el proveedor")).toBeInTheDocument();
    expect(screen.getByText(/no es la registrada/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Pedir corrección/ })).not.toBeInTheDocument();
  });

  it("shows that it is waiting for the supplier, and each round with its outcome and alert", async () => {
    const client = api();
    const received = { ...REQUEST, id: "r0", status: "received" as const, corrected_invoice_id: "INV-1", outcome: "hold" as const, alert: "La corrección trae una cuenta distinta a la registrada: quedó frenada." };
    vi.spyOn(client, "getCorrectionOffer").mockResolvedValue({ ...OFFER, open_request: REQUEST, history: [received, REQUEST] });
    renderWithApi(<CorrectionPanel invoiceId="F-039" cameByWhatsApp />, client);

    expect(await screen.findAllByText(/Esperando corrección del proveedor/)).not.toHaveLength(0);
    expect(screen.getByRole("link", { name: /Acta de la corrección INV-1/ })).toBeInTheDocument();
    expect(screen.getByText(/cuenta distinta a la registrada/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /WhatsApp/ })).toBeChecked();
  });

  it("stays out of the acta when there is nothing to say", async () => {
    const client = api();
    renderWithApi(<CorrectionPanel invoiceId="F-001" cameByWhatsApp={false} />, client);

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByText("Corrección con el proveedor")).not.toBeInTheDocument();
  });
});

describe("SupplierCorrection", () => {
  it("shows the one invoice and sends the confirmed amount", async () => {
    const client = api();
    vi.spyOn(client, "getSupplierCorrection").mockResolvedValue(VIEW);
    const confirm = vi
      .spyOn(client, "confirmSupplierCorrection")
      .mockResolvedValue({ received: true, message: "Recibimos su corrección." });
    renderWithApi(<SupplierCorrection token="tok" />, client);

    expect(await screen.findByText(/Cobalto Labs, Inc. necesita una corrección de la factura VO-11/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Monto/), "1900");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(confirm).toHaveBeenCalledWith("tok", { amount: "1900" });
    expect(await screen.findByText("Recibimos su corrección.")).toBeInTheDocument();
  });

  it("says plainly when the link no longer works", async () => {
    const client = api();
    vi.spyOn(client, "getSupplierCorrection").mockRejectedValue(
      new InvalidRequestError("Con este enlace ya se envió una corrección. Cada enlace sirve una sola vez.", 410),
    );
    renderWithApi(<SupplierCorrection token="tok" />, client);

    expect(await screen.findByText(/Cada enlace sirve una sola vez/)).toBeInTheDocument();
  });
});

describe("waitingInvoices", () => {
  it("lists only the invoices still waiting for their supplier", () => {
    expect(waitingInvoices([REQUEST, { ...REQUEST, invoice_id: "F-030", status: "received" }])).toEqual(new Set(["F-039"]));
  });
});
