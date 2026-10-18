import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { watch } from "./problems";

/**
 * How Custodio pays through Stripe, as the demo shows it: the payment on its way to Stripe and back with its tr_ id,
 * the acta's live proof checked field by field, /pagos with the record matched against Stripe and the pain.001 file
 * for Blinka. Stripe is the fake transport under the real SDK (see stripe.config.ts), so every id is tr_fake….
 */

const SENDING_HOLD_MS = 800;
const SHOTS = path.resolve(__dirname, "../../../docs/lanes/reports/L22");
const ERROR_SCREENS = [/This page couldn.t load/, /Application error/, /No pudimos cargar esto/];

async function expectNoErrorScreen(page: Page) {
  for (const screen of ERROR_SCREENS) await expect(page.getByText(screen)).toHaveCount(0);
}

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

test("pagar por Stripe se ve: el envío, el comprobante en vivo, el cuadre y el archivo para Blinka", async ({ page }, info) => {
  const shot = (name: string) => path.join(SHOTS, `${info.project.name}-${name}.png`);
  const problems = watch(page);

  await test.step("panel: la demo decide sus facturas y paga por Stripe", async () => {
    await page.goto("/");
    await page.getByRole("link", { name: /Probar la demo/ }).first().click();
    await expect(page).toHaveURL(/\/panel$/);
    const received = page.getByRole("region", { name: "Facturas por decidir" });
    await received.getByRole("button", { name: /Decidir las \d+ facturas/ }).click();
    await expect(page.getByText(/Custodio decidió \d+ facturas/)).toBeVisible();
    await expect(page.getByText("Riel: Stripe · modo prueba").first()).toBeVisible();
  });

  await test.step("acta: aprobar muestra «Enviando a Stripe…» y luego «Pagado · tr_…»", async () => {
    await page.goto("/panel?acta=F-003");
    const acta = page.getByRole("dialog");
    await expect(acta.getByText("Acta de decisión · F-003")).toBeVisible();
    // The fake Stripe answers in milliseconds; holding the approval a moment lets the walk see the step in flight.
    await page.route("**/api/v1/decisions/F-003/approve", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, SENDING_HOLD_MS));
      await route.continue();
    });
    await acta.getByRole("button", { name: /Aprobar pago/ }).click();
    const status = acta.getByLabel("Estado del pago");
    await expect(status).toContainText("Enviando a Stripe…");
    await acta.screenshot({ path: shot("1-enviando") });
    await expect(status).toContainText(/Pagado · tr_fake\d+/);
    await expect(acta.getByRole("region", { name: "Ejecución del pago" })).toContainText(/tr_fake\d+/);
    await acta.screenshot({ path: shot("2-pagado") });
    await page.keyboard.press("Escape");
  });

  await test.step("acta: «Pago en Stripe» trae la transferencia en vivo y la coteja con el acta", async () => {
    await page.goto("/panel?acta=F-004");
    const acta = page.getByRole("dialog");
    const proof = acta.getByRole("region", { name: "Pago en Stripe" });
    await expect(proof.getByText(/Stripe confirma el pago/)).toBeVisible();
    await expect(proof).toContainText(/Verificado en Stripe hace \d+ s/);
    await expect(proof.getByRole("list", { name: "Cotejo con el acta" }).getByLabel("coincide")).toHaveCount(6);
    await expect(proof).toContainText("livemode");
    await proof.getByText("Respuesta de Stripe (JSON)").click();
    await expect(proof.locator("pre")).toContainText('"object": "transfer"');
    await proof.scrollIntoViewIfNeeded();
    await proof.screenshot({ path: shot("3-pago-en-stripe") });
    await expect(proof.getByRole("link", { name: /Abrir en Stripe/ })).toHaveAttribute(
      "href",
      /^https:\/\/dashboard\.stripe\.com\/test\/connect\/transfers\/tr_fake\d+$/,
    );
    await expectNoHorizontalScroll(page);
    await page.keyboard.press("Escape");
  });

  await test.step("pagos: el registro de Custodio cuadra con Stripe y el lote sale en pain.001", async () => {
    await page.getByRole("navigation", { name: "Secciones" }).getByRole("link", { name: "Pagos" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Pagos" })).toBeVisible();
    const match = page.getByRole("region", { name: "Registro de Custodio ↔ Stripe" });
    await expect(match).toContainText(/Cuadra: \d+ pagos del registro, \d+ transferencias en Stripe/);
    await expect(match.getByText("Diferencia").locator("..")).toContainText("USD 0,00");
    await expect(page.getByRole("region", { name: "Pagos del espacio" }).getByRole("link", { name: /tr_fake/ }).first()).toBeVisible();
    await expectNoHorizontalScroll(page);
    await expectNoErrorScreen(page);
    await page.screenshot({ path: shot("4-pagos"), fullPage: true });

    const card = page.getByRole("region", { name: "Archivo para Blinka" });
    await expect(card).toContainText("Listo para que Blinka lo pague");
    const download = page.waitForEvent("download");
    await card.getByRole("button", { name: /Descargar pain\.001/ }).click();
    const file = await (await download).path();
    const xml = await readFile(file, "utf8");
    expect(xml).toContain("urn:iso:std:iso:20022:tech:xsd:pain.001.001.09");
    expect(xml).toContain("<EndToEndId>F-003</EndToEndId>");
  });

  await test.step("pagos: el acta abre desde la lista", async () => {
    await page.getByRole("region", { name: "Pagos del espacio" }).getByRole("link", { name: "F-004" }).click();
    await expect(page.getByRole("dialog").getByText("Acta de decisión · F-004")).toBeVisible();
    await expect(page.getByRole("dialog").getByRole("region", { name: "Pago en Stripe" })).toBeVisible();
  });

  expect(problems.list).toEqual([]);
});
