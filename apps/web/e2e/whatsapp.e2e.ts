import { createHmac, randomUUID } from "node:crypto";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { E2E_API_URL, WHATSAPP_E2E } from "./playwright.config";
import { watch } from "./problems";

/**
 * A phone linked from the panel sends an invoice on WhatsApp and the panel shows it decided seconds later. Meta is
 * played by this test: each delivery is signed with the app secret, exactly as Meta signs it.
 */

const PHONE = "573001234567";
const SUPPLIER = "Papelería El Mensajero";
const INVOICE = [
  `Proveedor: ${SUPPLIER}`,
  "Identificación tributaria: 900765432",
  "Número de factura: FV-WA-2041",
  "Fecha de emisión: 2026-10-15",
  "Monto: 180.00",
  "Moneda: USD",
  "Banco: Banco Andino",
  "Cuenta: 123456789",
  "Concepto: Resmas de papel",
].join("\n");

async function deliver(request: APIRequestContext, text: string) {
  const delivery = {
    object: "whatsapp_business_account",
    entry: [
      {
        id: "102290129340398",
        changes: [
          {
            field: "messages",
            value: {
              messaging_product: "whatsapp",
              metadata: { display_phone_number: WHATSAPP_E2E.WHATSAPP_DISPLAY_NUMBER, phone_number_id: WHATSAPP_E2E.WHATSAPP_PHONE_NUMBER_ID },
              messages: [{ from: PHONE, id: `wamid.${randomUUID()}`, timestamp: "1760749200", type: "text", text: { body: text } }],
            },
          },
        ],
      },
    ],
  };
  const body = JSON.stringify(delivery);
  const signature = `sha256=${createHmac("sha256", WHATSAPP_E2E.WHATSAPP_APP_SECRET).update(body).digest("hex")}`;
  const response = await request.post(`${E2E_API_URL}/api/v1/whatsapp/webhook`, {
    data: body,
    headers: { "Content-Type": "application/json", "X-Hub-Signature-256": signature },
  });
  expect(response.status()).toBe(200);
}

test("a phone linked from the panel sends an invoice and the panel shows it on its own", async ({ page, request }) => {
  const problems = watch(page);
  await page.goto("/");
  await page.getByRole("link", { name: /Probar la demo/ }).first().click();
  await expect(page).toHaveURL(/\/panel$/);

  const card = page.getByRole("region", { name: "Recibe facturas por WhatsApp" });
  await card.getByRole("button", { name: "Ligar mi teléfono" }).click();
  const code = (await card.getByLabel("Código de un solo uso").textContent())?.trim() ?? "";
  expect(code).toMatch(/^[A-Z2-9]{6}$/);
  await expect(card.getByRole("link", { name: "Abrir WhatsApp" })).toHaveAttribute("href", new RegExp(`wa\\.me/15550783881\\?text=Vincular%20${code}`));

  await deliver(request, `Vincular ${code}`);
  await expect(card.getByRole("list", { name: "Teléfonos ligados" })).toContainText("+57 ••• 4567");

  await deliver(request, INVOICE);
  await expect(page.getByText(SUPPLIER).first()).toBeVisible();
  expect(problems.list).toEqual([]);
});
