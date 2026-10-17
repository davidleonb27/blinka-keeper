import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { ReconciliationPage } from "./reconciliation-page";

async function withDemoStatement() {
  const api = createMockClient({ latencyMs: 0 });
  renderWithApi(<ReconciliationPage />, api);
  await userEvent.click(await screen.findByRole("button", { name: /Usar extracto de demo/ }));
  await screen.findByRole("region", { name: "Alertas" });
  return api;
}

describe("ReconciliationPage", () => {
  it("offers to drop a statement or use the demo one before anything is reconciled", async () => {
    renderWithApi(<ReconciliationPage />);

    expect(await screen.findByRole("button", { name: /Usar extracto de demo/ })).toBeInTheDocument();
    expect(screen.getByLabelText(/Arrastra el extracto/)).toBeInTheDocument();
  });

  it("shows reconciled movements, differences and alerts in three columns with their reasons", async () => {
    await withDemoStatement();

    const reconciled = screen.getByRole("region", { name: "Conciliado" });
    const differences = screen.getByRole("region", { name: "Con diferencia" });
    const alerts = screen.getByRole("region", { name: "Alertas" });
    expect(within(reconciled).getByText(/PAGO PULSO SOFTWARE/)).toBeInTheDocument();
    expect(within(reconciled).getAllByText("Partido")).toHaveLength(2);
    expect(within(reconciled).getByRole("link", { name: /Acta F-005/ })).toHaveAttribute("href", "/panel?acta=F-005");
    expect(within(differences).getByText(/KORA TRADUCCIONES/)).toBeInTheDocument();
    expect(within(differences).getByText(/COMISION ENVIO SWIFT/)).toBeInTheDocument();
    expect(within(alerts).getByText(/ORBIT GROWTH PARTNERS/)).toBeInTheDocument();
    expect(within(alerts).getByText(/esperaba aprobación/)).toBeInTheDocument();
    expect(screen.getByText(/F-036/)).toBeInTheDocument();
  });

  it("closes the month only after every alert was reviewed, then offers the evidence pack", async () => {
    const api = await withDemoStatement();
    const download = vi.spyOn(api, "downloadEvidence").mockResolvedValue(new Blob(["PK"]));
    URL.createObjectURL = vi.fn(() => "blob:paquete");
    URL.revokeObjectURL = vi.fn();
    const save = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const closing = screen.getByRole("region", { name: "Cierre del mes" });
    expect(within(closing).getByRole("button", { name: /Cerrar octubre/ })).toBeDisabled();

    const alerts = screen.getByRole("region", { name: "Alertas" });
    for (const form of within(alerts).getAllByRole("form", { name: /Revisar/ })) {
      await userEvent.type(within(form).getByLabelText("Nota de revisión"), "Revisado con el banco.");
      await userEvent.type(within(form).getByLabelText("Quién revisa"), "Ana Gómez");
      await userEvent.click(within(form).getByRole("button", { name: /Marcar como revisado/ }));
    }
    await within(alerts).findAllByText(/Revisó Ana Gómez/);

    await userEvent.type(within(closing).getByLabelText("Quién cierra"), "Ana Gómez");
    await userEvent.click(within(closing).getByRole("button", { name: /Cerrar octubre/ }));
    await within(closing).findByText(/Mes cerrado por Ana Gómez/);
    await userEvent.click(within(closing).getByRole("button", { name: /Descargar el paquete/ }));

    expect(download).toHaveBeenCalledWith("2026-10");
    expect(save.mock.contexts[0]).toHaveProperty("download", "custodio-cierre-2026-10.zip");
  });
});
