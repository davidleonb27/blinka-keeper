import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { MOCK_RECEIPT_KEY } from "@/lib/api/mock/receipts";
import { renderWithApi } from "@/test/render";
import { VerifyPage } from "./verify-page";

async function paste(text: string) {
  const box = screen.getByLabelText("Recibo (JSON)");
  fireEvent.change(box, { target: { value: text } });
  await userEvent.click(screen.getByRole("button", { name: /^Verificar$/ }));
}

describe("VerifyPage", () => {
  it("shows the public key it checks with", async () => {
    renderWithApi(<VerifyPage />);

    expect(await screen.findByText(MOCK_RECEIPT_KEY.key_id)).toBeInTheDocument();
  });

  it("names the altered amount in the browser and on the server", async () => {
    renderWithApi(<VerifyPage />);
    await screen.findByText(MOCK_RECEIPT_KEY.key_id);

    await userEvent.click(screen.getByRole("button", { name: /Probar con un recibo alterado/ }));

    const browser = await screen.findByRole("region", { name: "En tu navegador" });
    const server = await screen.findByRole("region", { name: "En el servidor de Blinka Keeper" });
    expect(browser).toHaveTextContent("Inválido: el campo monto fue alterado después de firmarse.");
    expect(server).toHaveTextContent("Inválido: el campo monto fue alterado después de firmarse.");
    expect(screen.getByText(/cambiamos el monto de/)).toBeInTheDocument();
  });

  it("says a genuine receipt is valid and what the decision was", async () => {
    const api = createMockClient({ latencyMs: 0 });
    const receipt = await api.getExampleReceipt();
    renderWithApi(<VerifyPage />, api);
    await screen.findByText(MOCK_RECEIPT_KEY.key_id);

    await paste(JSON.stringify(receipt));

    const browser = await screen.findByRole("region", { name: "En tu navegador" });
    expect(browser).toHaveTextContent(/Válido: firmado por Blinka Keeper/);
    expect(within(browser).getByText("Pagar")).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "En el servidor de Blinka Keeper" })).toHaveTextContent(/Válido/);
  });

  it("says when the text is not JSON at all", async () => {
    renderWithApi(<VerifyPage />);
    await screen.findByText(MOCK_RECEIPT_KEY.key_id);

    await paste("esto no es un recibo");

    expect(await screen.findByRole("region", { name: "En tu navegador" })).toHaveTextContent("el texto no es JSON");
  });
});
