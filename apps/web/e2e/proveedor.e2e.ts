import { expect, test } from "@playwright/test";
import { watch } from "./problems";

/**
 * The whole supplier-correction cycle against the real API: the company asks from the acta of an invoice stopped for
 * a cause the supplier can fix, the supplier (another browser, no workspace) confirms the amount on the public page,
 * and the corrected invoice is decided by the same rules and paid alone; the original can no longer be paid.
 */

const SEEDED = "F-039"; // Valentina Ortiz: the amount of a WhatsApp photo could not be read with confidence
const WORKSPACE_COOKIE = "custodio_ws";
const LINK = /\/proveedor\/c\/[\w-]+/;

test("a supplier corrects a stopped invoice from a link and it is paid alone", async ({ page, browser, request, baseURL }) => {
  const problems = watch(page);
  const created = await (await request.post("/api/v1/workspaces", { data: { mode: "demo" } })).json();
  const headers = { "X-Custodio-Workspace": created.workspace_id };
  expect((await request.post("/api/v1/invoices/process", { headers })).ok()).toBe(true);
  await page.context().addCookies([{ name: WORKSPACE_COOKIE, value: created.workspace_id, url: baseURL ?? "" }]);

  let link = "";
  await test.step("empresa: pide la corrección desde el acta", async () => {
    await page.goto(`/panel?acta=${SEEDED}`);
    const acta = page.getByRole("dialog");
    await expect(acta.getByText(/no se pudo leer con certeza/)).toBeVisible();
    await acta.getByRole("button", { name: "Pedir corrección al proveedor" }).click();
    const message = await acta.getByRole("textbox").inputValue();
    link = message.match(LINK)?.[0] ?? "";
    expect(link).not.toBe("");
    await expect(acta.getByText("Esperando corrección del proveedor").first()).toBeVisible();
  });

  await test.step("proveedor: confirma el monto desde otra sesión", async () => {
    const supplier = await (await browser.newContext()).newPage();
    const supplierProblems = watch(supplier);
    await supplier.goto(link);
    await expect(supplier.getByRole("heading", { name: /necesita una corrección de la factura VO-11/ })).toBeVisible();
    await supplier.getByLabel("Monto").fill("1900");
    await supplier.getByRole("button", { name: "Confirmar" }).click();
    await expect(supplier.getByText("Corrección enviada")).toBeVisible();
    expect(supplierProblems.list).toEqual([]);
  });

  await test.step("empresa: la corrección se pagó sola y la original ya no se paga", async () => {
    await page.reload();
    const acta = page.getByRole("dialog");
    await expect(acta.getByText(/ya no se paga/)).toBeVisible();
    await acta.getByRole("link", { name: /Acta de la corrección/ }).click();
    await expect(page.getByRole("dialog").getByText("Pagada sola").first()).toBeVisible();
    await page.goto("/panel");
    await expect(page.getByRole("region", { name: "Resueltas con el proveedor" })).toContainText("1 de 1 pedidas");
  });

  expect(problems.list).toEqual([]);
});
