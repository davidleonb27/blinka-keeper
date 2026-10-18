import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { AgreementPreview } from "@/lib/api/client";
import type { Decision } from "@/lib/api/contracts";
import { DEMO } from "@/lib/api/mock/dataset";
import { ApprovalChoices } from "./approval-choices";

function decisionOf(id: string): Decision {
  const item = DEMO.items.find((i) => i.decision.invoice_id === id);
  if (!item) throw new Error(`missing ${id}`);
  return item.decision;
}

const PREVIEW: AgreementPreview = {
  policy_version: 3,
  changes: [
    {
      field: "beneficiaries[b3].agreement.amount",
      label: "Monto acordado con Pixel Norte S.A. de C.V.",
      before: "58000",
      after: "61000",
      source_quote: "",
    },
  ],
  simulation: {
    before: { total: 1, paid_auto: 0, paid_human: 0, hold: 0, pending: 1, rejected: 0, autonomy_rate: 0, improper_payments: 0 },
    after: { total: 1, paid_auto: 1, paid_human: 0, hold: 0, pending: 0, rejected: 0, autonomy_rate: 1, improper_payments: 0 },
    changed: [],
  },
};

function renderChoices(id: string, preview = vi.fn().mockResolvedValue(PREVIEW)) {
  const onDecide = vi.fn();
  render(
    <ApprovalChoices decision={decisionOf(id)} approvers={["Ana Gómez"]} onDecide={onDecide} onPreviewAgreement={preview} deciding={false} />,
  );
  return { onDecide, preview };
}

describe("ApprovalChoices", () => {
  it("never suggests one invoice's amount as a supplier's monthly cap", async () => {
    const decision = decisionOf("F-019");
    const cap = { kind: "monthly_cap" as const, amount: 60000000, currency: "COP", critical: false };
    render(
      <ApprovalChoices decision={decision} approvers={["Ana Gómez"]} agreement={cap} onDecide={vi.fn()} onPreviewAgreement={vi.fn()} deciding={false} />,
    );
    await userEvent.type(screen.getByLabelText(/Motivo/), "Nuevo contrato");
    await userEvent.click(screen.getByRole("button", { name: /Aprobar y actualizar el acuerdo/ }));

    expect(screen.getByLabelText(/Nuevo tope mensual \(\s*COP\)/)).toHaveValue("");
  });

  it("asks for a reason before approving only this once", async () => {
    const { onDecide } = renderChoices("F-019");
    const once = screen.getByRole("button", { name: /Aprobar sólo esta vez/ });

    await userEvent.click(once);
    expect(onDecide).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/motivo/);
    expect(screen.getByLabelText(/Motivo/)).toHaveFocus();

    await userEvent.type(screen.getByLabelText(/Motivo/), "Subió el precio");
    await userEvent.click(once);

    expect(onDecide).toHaveBeenCalledWith({ kind: "once", approver: "Ana Gómez", reason: "Subió el precio" });
  });

  it("offers one-click reasons that approve only this once", async () => {
    const { onDecide } = renderChoices("F-019");
    await userEvent.click(screen.getByRole("button", { name: "Confirmado con el proveedor" }));
    await userEvent.click(screen.getByRole("button", { name: /Aprobar sólo esta vez/ }));

    expect(onDecide).toHaveBeenCalledWith({ kind: "once", approver: "Ana Gómez", reason: "Confirmado con el proveedor" });
  });

  it("simulates the new agreement before it can be confirmed, and confirms against the simulated version", async () => {
    const { onDecide, preview } = renderChoices("F-019");
    await userEvent.type(screen.getByLabelText(/Motivo/), "Nuevo contrato firmado");
    await userEvent.click(screen.getByRole("button", { name: /Aprobar y actualizar el acuerdo/ }));
    const amount = screen.getByLabelText(/Nuevo monto acordado/);
    await userEvent.clear(amount);
    await userEvent.type(amount, "61000");

    expect(screen.getByRole("button", { name: /Confirmar/ })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /Simular el cambio/ }));
    expect(preview).toHaveBeenCalledWith({ amount: "61000", tolerance_pct: null });
    expect(await screen.findByText(/Monto acordado con Pixel Norte/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /guardar la versión 4/ }));

    expect(onDecide).toHaveBeenCalledWith({
      kind: "agreement",
      approver: "Ana Gómez",
      reason: "Nuevo contrato firmado",
      agreement: { amount: "61000", tolerance_pct: null },
      expectedVersion: 3,
    });
  });

  it("drops the simulation when the agreement is edited after it", async () => {
    renderChoices("F-019");
    await userEvent.type(screen.getByLabelText(/Motivo/), "Nuevo contrato firmado");
    await userEvent.click(screen.getByRole("button", { name: /Aprobar y actualizar el acuerdo/ }));
    await userEvent.click(screen.getByRole("button", { name: /Simular el cambio/ }));
    await screen.findByText(/Monto acordado con Pixel Norte/);

    await userEvent.type(screen.getByLabelText(/Tolerancia de este proveedor/), "5");

    expect(screen.getByRole("button", { name: /Confirmar/ })).toBeDisabled();
  });

  it("leaves only the rejection when a hard rule fails", async () => {
    const { onDecide } = renderChoices("F-022");

    expect(screen.getByRole("note")).toHaveTextContent(/No se puede aprobar: R2/);
    expect(screen.getByRole("button", { name: /Aprobar sólo esta vez/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Aprobar y actualizar el acuerdo/ })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /Rechazar/ }));
    expect(onDecide).toHaveBeenCalledWith({ kind: "reject", approver: "Ana Gómez" });
  });

  it("offers no agreement to update for an unknown supplier", () => {
    renderChoices("F-015");

    expect(screen.queryByRole("button", { name: /Aprobar y actualizar el acuerdo/ })).not.toBeInTheDocument();
  });
});
