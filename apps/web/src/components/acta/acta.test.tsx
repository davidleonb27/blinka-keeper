import { render as renderComponent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DEMO } from "@/lib/api/mock/dataset";
import { Acta } from "./acta";

function demoItem(id: string) {
  const item = DEMO.items.find((i) => i.decision.invoice_id === id);
  if (!item) throw new Error(`missing ${id}`);
  return item;
}

const approvers = DEMO.policy.approvers;

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

    expect(screen.getByText(/Texto oculto destapado/)).toBeInTheDocument();
    expect(screen.getByText(/Nota para el asistente de IA/)).toBeInTheDocument();
  });

  it("shows its place in the ledger", () => {
    const item = demoItem("F-020");
    render(item);

    expect(screen.getByText(`Asiento #${item.ledger?.seq}`)).toBeInTheDocument();
  });

  it("lets a person approve or reject a pending invoice", async () => {
    const onDecide = vi.fn();
    render(demoItem("F-015"), onDecide);

    await userEvent.click(screen.getByRole("button", { name: /Aprobar pago/ }));
    expect(onDecide).toHaveBeenCalledWith(true, "Ana Gómez");

    await userEvent.click(screen.getByRole("button", { name: /Rechazar/ }));
    expect(onDecide).toHaveBeenCalledWith(false, "Ana Gómez");
  });

  it("offers no approval for an invoice the agent already paid", () => {
    render(demoItem("F-001"));

    expect(screen.queryByRole("button", { name: /Aprobar pago/ })).not.toBeInTheDocument();
    expect(screen.getByText("Pagada sola")).toBeInTheDocument();
  });
});

function render(item: ReturnType<typeof demoItem>, onDecide = vi.fn()) {
  return renderComponent(<Acta detail={item} approvers={approvers} onDecide={onDecide} deciding={false} />);
}
