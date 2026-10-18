import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Decision } from "@/lib/api/contracts";
import { DEMO } from "@/lib/api/mock/dataset";
import { PaymentProgress } from "./payment-progress";

function approved(execution: Decision["execution"]): Decision {
  const item = DEMO.items.find((i) => i.decision.invoice_id === "F-001");
  if (!item) throw new Error("missing F-001");
  return { ...structuredClone(item.decision), status: "paid_human", execution };
}

describe("PaymentProgress", () => {
  it("says the payment is on its way to Stripe while the approval is in flight", () => {
    render(<PaymentProgress step={{ phase: "sending", rail: "stripe_test" }} />);

    expect(screen.getByLabelText("Estado del pago")).toHaveTextContent("Enviando a Stripe…");
  });

  it("then shows the transfer id Stripe answered", () => {
    const decision = approved({
      rail: "stripe_test",
      status: "executed",
      external_id: "tr_1Qx7",
      dashboard_url: null,
      executed_at: "2026-10-17T15:00:00Z",
      error: null,
    });
    render(<PaymentProgress step={{ phase: "done", decision }} />);

    expect(screen.getByLabelText("Estado del pago")).toHaveTextContent("Pagado · tr_1Qx7");
  });

  it("reflects a failed transfer instead of claiming it was paid", () => {
    const decision = approved({
      rail: "stripe_test",
      status: "failed",
      external_id: null,
      dashboard_url: null,
      executed_at: "2026-10-17T15:00:00Z",
      error: "Stripe rechazó el pago; no se transfirió dinero.",
    });
    render(<PaymentProgress step={{ phase: "done", decision }} />);

    const status = screen.getByLabelText("Estado del pago");
    expect(status).toHaveTextContent("No salió: Stripe rechazó el pago");
    expect(status).not.toHaveTextContent("Pagado");
  });

  it("says an approval that waits for its due date was not paid yet", () => {
    render(<PaymentProgress step={{ phase: "done", decision: approved(null) }} />);

    expect(screen.getByLabelText("Estado del pago")).toHaveTextContent("sale el día que vence");
  });
});
