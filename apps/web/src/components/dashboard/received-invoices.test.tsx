import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { describe, expect, it, vi } from "vitest";
import { Toaster } from "@/components/ui/sonner";
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

  it("still confirms what was decided after the banner goes away", async () => {
    const api = createMockClient({ latencyMs: 0 });
    const { unmount } = renderWithApi(
      <>
        <ReceivedInvoices count={27} />
        <Toaster />
      </>,
      api,
    );
    vi.spyOn(api, "processInvoices").mockImplementation(async () => {
      unmount();
      return createMockClient({ latencyMs: 0 }).processInvoices();
    });
    const success = vi.spyOn(toast, "success");

    await userEvent.click(screen.getByRole("button", { name: /Decidir las 27 facturas/ }));

    await vi.waitFor(() => expect(success).toHaveBeenCalledWith(expect.stringMatching(/Custodio decidió \d+ facturas/)));
  });

  it("speaks of a single invoice in singular", () => {
    renderWithApi(<ReceivedInvoices count={1} />);

    expect(screen.getByText(/1 factura recibida/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Decidir la factura/ })).toBeInTheDocument();
  });

  it("opens the panel with where the invoices came from and shows progress while it decides", async () => {
    const api = createMockClient({ latencyMs: 0 });
    vi.spyOn(api, "processInvoices").mockImplementation(() => new Promise(() => {}));
    renderWithApi(<ReceivedInvoices count={38} first />, api);

    expect(screen.getByText("38 facturas recibidas: correo, PDF, foto, WhatsApp")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Decidir las 38 facturas/ }));

    expect(await screen.findByRole("status")).toHaveTextContent(/Leyendo cada documento/);
    expect(screen.getByRole("button", { name: /Decidiendo/ })).toBeDisabled();
  });
});
