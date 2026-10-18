import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MOCK_RECEIPT_KEY } from "@/lib/api/mock/receipts";
import { verifyReceiptInBrowser } from "@/lib/receipts/verify";
import { renderWithApi } from "@/test/render";
import { SignedReceipt } from "./signed-receipt";

afterEach(() => vi.restoreAllMocks());

describe("SignedReceipt", () => {
  it("seals the acta with the id of the key that signed it", async () => {
    renderWithApi(<SignedReceipt invoiceId="F-001" />);

    expect(await screen.findByText(MOCK_RECEIPT_KEY.key_id)).toBeInTheDocument();
    expect(screen.getByLabelText("Recibo firmado")).toHaveTextContent(`Firmado · clave ${MOCK_RECEIPT_KEY.key_id}`);
    expect(screen.getByRole("link", { name: "Verificar un recibo" })).toHaveAttribute("href", "/verificar");
  });

  it("downloads a receipt that checks with the public key", async () => {
    const saved: Blob[] = [];
    vi.spyOn(URL, "createObjectURL").mockImplementation((blob) => {
      saved.push(blob as Blob);
      return "blob:recibo";
    });
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const { api } = renderWithApi(<SignedReceipt invoiceId="F-001" />);
    await api.processInvoices();

    await userEvent.click(screen.getByRole("button", { name: /Descargar recibo firmado/ }));

    await waitFor(() => expect(saved).toHaveLength(1));
    const receipt: unknown = JSON.parse(await saved[0].text());
    expect(verifyReceiptInBrowser(receipt, MOCK_RECEIPT_KEY).valid).toBe(true);
  });
});
