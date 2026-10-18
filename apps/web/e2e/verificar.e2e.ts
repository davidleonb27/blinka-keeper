import { expect, test } from "@playwright/test";
import { watch } from "./problems";

/** The public receipt check, against the real API: a genuine receipt verifies, an altered one names the field. */

test("anyone checks a signed receipt in the browser and on the server", async ({ page }) => {
  const problems = watch(page);

  await test.step("seguridad enlaza a la verificación pública", async () => {
    await page.goto("/docs/seguridad");
    await page.getByRole("link", { name: "Verificar un recibo" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Verifica un recibo de Custodio" })).toBeVisible();
    await expect(page.getByText(/Clave pública cust-[0-9a-f]{16}/)).toBeVisible();
  });

  await test.step("un recibo alterado: el monto", async () => {
    await page.getByRole("button", { name: /Probar con un recibo alterado/ }).click();
    const altered = "Inválido: el campo monto fue alterado después de firmarse.";
    await expect(page.getByRole("region", { name: "En tu navegador" })).toContainText(altered);
    await expect(page.getByRole("region", { name: "En el servidor de Custodio" })).toContainText(altered);
  });

  await test.step("un recibo genuino es válido en los dos lados", async () => {
    const example = await (await page.request.get("/api/v1/receipts/example")).text();
    await page.getByLabel("Recibo (JSON)").fill(example);
    await page.getByRole("button", { name: "Verificar", exact: true }).click();
    await expect(page.getByRole("region", { name: "En tu navegador" })).toContainText("Válido: firmado por Custodio");
    await expect(page.getByRole("region", { name: "En el servidor de Custodio" })).toContainText("la decisión fue «Pagar»");
  });

  expect(problems.list, problems.list.join("\n")).toEqual([]);
});
