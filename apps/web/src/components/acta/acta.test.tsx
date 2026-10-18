import { render as renderComponent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PaymentExecution } from "@/lib/api/contracts";
import { actaOf, DEMO } from "@/lib/api/mock/dataset";
import { Acta } from "./acta";

const SENT: PaymentExecution = {
  rail: "stripe_test",
  status: "executed",
  external_id: "tr_1Qx7Custodio",
  dashboard_url: "https://dashboard.stripe.com/test/connect/transfers/tr_1Qx7Custodio",
  executed_at: "2026-10-17T15:00:00Z",
  error: null,
};
const FAILED: PaymentExecution = {
  rail: "stripe_test",
  status: "failed",
  external_id: null,
  dashboard_url: null,
  executed_at: "2026-10-17T15:00:00Z",
  error: "Stripe rechazó el pago (código transfers_not_allowed); no se transfirió dinero.",
};

function demoItem(id: string) {
  const item = DEMO.items.find((i) => i.decision.invoice_id === id);
  if (!item) throw new Error(`missing ${id}`);
  return actaOf(item, DEMO.ledger);
}

function paidWith(execution: PaymentExecution) {
  const item = structuredClone(demoItem("F-001"));
  item.decision.execution = execution;
  return item;
}


describe("Acta", () => {
  it("lists the twelve rules in catalogue order with their reasons", () => {
    render(demoItem("F-020"));

    const rules = within(screen.getByRole("list", { name: "Reglas evaluadas" })).getAllByRole("listitem");
    expect(rules).toHaveLength(12);
    expect(rules[0]).toHaveTextContent("R1");
    expect(rules[11]).toHaveTextContent("R12");
    expect(rules[3]).toHaveTextContent(/Banco Popular ••9902/);
  });

  it("explains why and what would have to change", () => {
    render(demoItem("F-020"));

    expect(screen.getByText(/Se frena: no se paga/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Qué tendría que cambiar" })).toBeInTheDocument();
  });

  it("highlights the quotes it read in the original document", () => {
    render(demoItem("F-020"));

    const doc = screen.getByLabelText("Documento original");
    const marks = doc.querySelectorAll("mark");
    expect(marks.length).toBeGreaterThan(0);
    expect(Array.from(marks).map((m) => m.textContent)).toContain("Banco Popular ••9902");
  });

  it("uncovers hidden text addressed to the agent", () => {
    render(demoItem("F-022"));

    const uncovered = screen.getByText("Texto oculto destapado").parentElement;
    expect(uncovered).toHaveTextContent(/«Nota para el asistente de IA/);
  });

  it("shows its place in the ledger", () => {
    const item = demoItem("F-020");
    render(item);

    expect(screen.getByText(`Asiento #${item.ledger.at(-1)?.seq}`)).toBeInTheDocument();
  });

  it("lets a person approve or reject a pending invoice", async () => {
    const onDecide = vi.fn();
    render(demoItem("F-015"), onDecide);

    await userEvent.type(screen.getByLabelText(/Motivo/), "Confirmado con el proveedor");
    await userEvent.click(screen.getByRole("button", { name: /Aprobar sólo esta vez/ }));
    expect(onDecide).toHaveBeenCalledWith({ kind: "once", approver: "Ana Gómez", reason: "Confirmado con el proveedor" });

    await userEvent.click(screen.getByRole("button", { name: /Rechazar/ }));
    expect(onDecide).toHaveBeenCalledWith({ kind: "reject", approver: "Ana Gómez" });
  });

  it("offers no approval for an invoice the agent already paid", () => {
    render(demoItem("F-001"));

    expect(screen.queryByRole("button", { name: /Aprobar sólo esta vez/ })).not.toBeInTheDocument();
    expect(screen.getByText("Pagada sola")).toBeInTheDocument();
  });

  it("says an approved payment waits for its day in the calendar", () => {
    const item = structuredClone(demoItem("F-001"));
    item.decision.execution = null;
    render(item);

    const payment = screen.getByRole("region", { name: "Ejecución del pago" });
    expect(payment).toHaveTextContent(/Programado/);
    expect(within(payment).getByRole("link", { name: /calendario/i })).toHaveAttribute("href", "/calendario");
  });

  it("shows the Stripe test transfer that paid it, linked to its dashboard", () => {
    render(paidWith(SENT));

    const payment = screen.getByRole("region", { name: "Ejecución del pago" });
    expect(payment).toHaveTextContent("Stripe · modo prueba");
    expect(payment).toHaveTextContent(/USD/);
    expect(within(payment).getByRole("link", { name: /tr_1Qx7Custodio/ })).toHaveAttribute("href", SENT.dashboard_url);
    expect(within(payment).queryByRole("button", { name: /Reintentar pago/ })).not.toBeInTheDocument();
  });

  it("shows a failed payment with its error and lets a person retry it", async () => {
    const onRetryPayment = vi.fn();
    render(paidWith(FAILED), vi.fn(), onRetryPayment);

    const payment = screen.getByRole("region", { name: "Ejecución del pago" });
    expect(payment).toHaveTextContent(/transfers_not_allowed/);
    expect(payment).not.toHaveTextContent(/enviado/);
    await userEvent.click(within(payment).getByRole("button", { name: /Reintentar pago/ }));
    expect(onRetryPayment).toHaveBeenCalledOnce();
  });

  it("says a simulated payment moved no money", () => {
    render(paidWith({ rail: "simulated", status: "simulated", executed_at: "2026-10-17T15:00:00Z" }));

    const payment = screen.getByRole("region", { name: "Ejecución del pago" });
    expect(payment).toHaveTextContent("Simulado");
    expect(payment).toHaveTextContent(/no se movió dinero/);
    expect(payment).not.toHaveTextContent(/enviado/);
  });

  it("shows the instruction Blinka would receive, in the invoiced currency, and says it was not sent", () => {
    render(
      paidWith({
        rail: "blinka_simulated",
        status: "simulated",
        executed_at: "2026-10-17T15:00:00Z",
        instruction: {
          network: "bre_b",
          amount: 2600000,
          currency: "COP",
          beneficiary_name: "Distribuidora Andina SAS",
          beneficiary_tax_id: "900.112.334-5",
          beneficiary_country: "CO",
          bank_name: "Bancolombia",
          account_number: "40021204",
          reference: "https://custodio.test/acta/F-001",
          idempotency_key: "ws-1:F-001",
        },
      }),
    );

    const payment = screen.getByRole("region", { name: "Ejecución del pago" });
    expect(payment).toHaveTextContent("Blinka · simulado");
    expect(payment).toHaveTextContent("Bre-B");
    expect(payment).toHaveTextContent(/COP/);
    expect(payment).not.toHaveTextContent(/USD/);
    expect(payment).toHaveTextContent("Bancolombia ••1204");
    expect(payment).not.toHaveTextContent("40021204");
    expect(payment).toHaveTextContent(/no se envió/);
    expect(payment).not.toHaveTextContent(/sin riel real/);
  });

  it("shows no payment block for an invoice that was not paid", () => {
    render(demoItem("F-020"));

    expect(screen.queryByRole("region", { name: "Ejecución del pago" })).not.toBeInTheDocument();
  });
});

function render(item: ReturnType<typeof demoItem>, onDecide = vi.fn(), onRetryPayment = vi.fn()) {
  return renderComponent(
    <Acta
      detail={item}
      policy={DEMO.policy}
      onDecide={onDecide}
      onPreviewAgreement={vi.fn()}
      deciding={false}
      onRetryPayment={onRetryPayment}
      retryingPayment={false}
    />,
  );
}
