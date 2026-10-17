import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { ReceivedInvoices } from "./received-invoices";

describe("ReceivedInvoices", () => {
  it("says how many invoices arrived undecided and has Custodio decide them", async () => {
    const api = createMockClient({ latencyMs: 0 });
    const process = vi.spyOn(api, "processInvoices");
    renderWithApi(<ReceivedInvoices count={27} />, api);

    expect(screen.getByText(/27 facturas recibidas/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Decidir las 27 facturas/ }));

    expect(process).toHaveBeenCalledOnce();
  });

  it("speaks of a single invoice in singular", () => {
    renderWithApi(<ReceivedInvoices count={1} />);

    expect(screen.getByText(/1 factura recibida/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Decidir la factura/ })).toBeInTheDocument();
  });
});
