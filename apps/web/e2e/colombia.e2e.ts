import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { watch } from "./problems";

/**
 * A Colombian company from the landing, as QA found it broken in production: base currency COP, suppliers from the
 * template (no «moneda» column), one workspace for the whole set-up, and a COP invoice of a registered supplier that
 * is decided by the rules instead of being held for a missing exchange rate.
 */

const SHOTS = path.resolve(__dirname, "../../../docs/lanes/reports/L18b");
const TEMPLATE = [
  "nombre;nit;banco;cuenta;moneda;monto mensual",
  "Papelería Central SAS;900123456-1;Bancolombia;123-456789-01;;450000",
].join("\n");

function invoice(lines: Record<string, string>): string {
  return Object.entries(lines)
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
}

const FV_1001 = invoice({
  Proveedor: "Papelería Central SAS",
  "Identificación tributaria": "900123456-1",
  "Número de factura": "FV-1001",
  "Fecha de emisión": "2026-10-15",
  Monto: "450000.00",
  Moneda: "COP",
  Banco: "Bancolombia",
  Cuenta: "123-456789-01",
  Concepto: "Resmas y tóner de octubre",
});

const UNKNOWN = invoice({
  Proveedor: "Tintas del Norte SAS",
  "Identificación tributaria": "901999888-2",
  "Número de factura": "TN-77",
  "Fecha de emisión": "2026-10-15",
  Monto: "120000.00",
  Moneda: "COP",
  Banco: "Davivienda",
  Cuenta: "0550-1234",
  Concepto: "Tinta",
});

async function workspaceHeaders(page: Page) {
  const workspace = (await page.context().cookies()).find((cookie) => cookie.name === "custodio_ws")?.value ?? "";
  return { "X-Custodio-Workspace": workspace };
}

async function uploadAndDecide(page: Page, text: string) {
  await page.getByRole("button", { name: "Subir facturas" }).first().click();
  const dialog = page.getByRole("dialog", { name: "Subir facturas" });
  await dialog.getByLabel("O pega el texto de un correo con la factura").fill(text);
  await dialog.getByRole("button", { name: "Enviar el texto" }).click();
  await dialog.getByRole("button", { name: "Decidir 1 factura" }).click();
  await expect(page.getByText("Custodio decidió 1 factura.")).toBeVisible();
  await expect(dialog).toHaveCount(0);
}

test("a Colombian company sets up in COP from the template and its COP invoice is decided, not held", async ({
  page,
}, info) => {
  const wide = info.project.name === "bogota";
  const width = wide ? 1440 : 390;
  await page.setViewportSize({ width, height: wide ? 900 : 844 });
  const problems = watch(page);
  const created: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/v1/workspaces")) created.push(request.url());
  });
  const shot = (name: string) => page.screenshot({ path: path.join(SHOTS, `${name}-${width}.png`), fullPage: true });

  await test.step("empezar: una sola región principal, sin texto de la landing", async () => {
    await page.goto("/");
    await page.getByRole("main").getByRole("link", { name: "Usar con mi empresa" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "¿Cómo se llama tu empresa?" })).toBeVisible();
    // cacheComponents keeps the landing in the DOM, hidden (display: none), for an instant back navigation: only
    // one main is visible and in the accessibility tree.
    await expect(page.getByRole("main")).toHaveCount(1);
    await expect(page.locator("main:visible")).toHaveCount(1);
    await expect(page.getByRole("main")).not.toContainText("Tu analista de cuentas por pagar");
  });

  await test.step("perfil, COP y reglas con un ejemplo completo, aunque la página se recargue a mitad", async () => {
    const startProfile = async () => {
      await page.getByLabel("Nombre de la empresa").fill("Papelería El Trigal");
      await page.getByRole("button", { name: "Continuar" }).click();
      await page.getByRole("button", { name: "Se ve bien" }).click();
      await expect(page.getByRole("heading", { level: 1, name: "País, moneda y saldo" })).toBeVisible();
    };
    await startProfile();
    // A reload (a deploy, a closed laptop) must not leave a second workspace behind when the set-up ends.
    await page.reload();
    await startProfile();
    await page.getByLabel("País").selectOption("CO");
    await page.getByLabel("Moneda base").selectOption("COP");
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByLabel("Nombre de quien aprueba").first().fill("Ana Gómez");
    await page.getByRole("button", { name: "Continuar" }).click();
    const rules = page.getByLabel("Reglas");
    await expect(rules).toHaveValue(/\d.* COP/);
    await expect(rules).not.toHaveValue(/\[/);
    await rules.fill("Nada sobre 2.000.000 COP sin aprobación");
    await expect(page.getByRole("listitem").getByText(/Tope de aprobación automática/)).toBeVisible();
    await page.getByRole("button", { name: "Continuar" }).click();
  });

  await test.step("proveedores: la lista de ejemplo y la plantilla sin «moneda» se leen en COP", async () => {
    await expect(page.getByRole("heading", { level: 1, name: "¿A quién le pagas?" })).toBeVisible();
    const imported = page.getByRole("region", { name: "Beneficiarios importados" });
    await page.getByRole("button", { name: "Usar una lista de ejemplo" }).click();
    await expect(imported).toContainText("Distribuidora Andina SAS");
    await page.locator('input[type="file"]').setInputFiles({
      name: "proveedores.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(TEMPLATE),
    });
    await expect(imported).toContainText("Papelería Central SAS");
    await shot("proveedores");
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Tu primera semana, decidida" })).toBeVisible();
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("link", { name: /Ir al panel/ }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Panel" })).toBeVisible();
  });

  await test.step("el espacio queda en COP, con el país, y se creó un solo espacio", async () => {
    const headers = await workspaceHeaders(page);
    const summary = await (await page.request.get("/api/v1/workspaces/current", { headers })).json();
    expect(summary).toMatchObject({ company_name: "Papelería El Trigal", base_currency: "COP", mode: "blank" });
    const policy = await (await page.request.get("/api/v1/policy", { headers })).json();
    expect(policy.beneficiaries).toEqual([
      expect.objectContaining({
        name: "Papelería Central SAS",
        currency: "COP",
        agreement: expect.objectContaining({ currency: "COP", amount: 450000 }),
      }),
    ]);
    const ledger: { kind: string; payload: { company?: { country: string } } }[] = await (
      await page.request.get("/api/v1/ledger", { headers })
    ).json();
    expect(ledger.find((entry) => entry.payload.company)?.payload.company?.country).toBe("CO");
    expect(created).toHaveLength(1);
  });

  await test.step("FV-1001 de Papelería Central se decide con las reglas, no por falta de tasa", async () => {
    await uploadAndDecide(page, FV_1001);
    const headers = await workspaceHeaders(page);
    const [item] = await (await page.request.get("/api/v1/decisions", { headers })).json();
    expect(item.invoice_number).toBe("FV-1001");
    expect(["paid_auto", "pending_approval"]).toContain(item.decision.status);
    const r8 = item.decision.rules.find((rule: { rule_id: string }) => rule.rule_id === "R8");
    expect(r8.outcome).not.toBe("hold");
    // The agreement is in COP like the invoice: R6 compares them instead of escalating over the currency.
    const r6 = item.decision.rules.find((rule: { rule_id: string }) => rule.rule_id === "R6");
    expect(r6.outcome).toBe("pass");
    await page.waitForLoadState("networkidle");
    await shot("panel");
  });

  await test.step("un proveedor no registrado no se paga solo, y su acta enlaza a «Agregar proveedores»", async () => {
    await uploadAndDecide(page, UNKNOWN);
    await page
      .getByRole("region", { name: "Facturas", exact: true })
      .getByRole("link", { name: /Tintas del Norte/ })
      .click();
    const acta = page.getByRole("dialog");
    await expect(acta).toContainText("Tintas del Norte SAS no está entre tus proveedores registrados");
    const headers = await workspaceHeaders(page);
    const items: {
      invoice_number: string;
      decision: { status: string; rules: { rule_id: string; outcome: string }[] };
    }[] = await (await page.request.get("/api/v1/decisions", { headers })).json();
    const unknown = items.find((i) => i.invoice_number === "TN-77")?.decision;
    expect(unknown?.status).not.toMatch(/^paid/);
    // R3 (allowed beneficiary) is what stops it: the supplier is not on the list.
    expect(unknown?.rules.find((rule) => rule.rule_id === "R3")?.outcome).toBe("escalate");
    await acta.getByRole("link", { name: "Agregar proveedores" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Proveedores" })).toBeVisible();
  });

  await test.step("el faltante se agrega a mano y queda en COP", async () => {
    const form = page.getByRole("form", { name: "Agregar a mano" });
    await form.getByLabel("Nombre").fill("Tintas del Norte SAS");
    await form.getByLabel("NIT o identificación tributaria").fill("901999888-2");
    await form.getByLabel("Banco").fill("Davivienda");
    await form.getByLabel("Cuenta, como aparece en sus facturas").fill("0550-1234");
    await form.getByRole("button", { name: "Añadir a la vista previa" }).click();
    const preview = page.getByRole("region", { name: "Vista previa de los cambios" });
    await preview.getByRole("button", { name: "Agregar 1 proveedor" }).click();
    await expect(page.getByText(/Se agregó 1 proveedor\./)).toBeVisible();
    const policy = await (await page.request.get("/api/v1/policy", { headers: await workspaceHeaders(page) })).json();
    expect(policy.beneficiaries).toContainEqual(
      expect.objectContaining({ name: "Tintas del Norte SAS", currency: "COP" }),
    );
    await page.goto("/panel");
    await expect(page.getByRole("heading", { level: 1, name: "Panel" })).toBeVisible();
  });

  await test.step("el CSV nunca deja vacío el id de transferencia", async () => {
    const download = page.waitForEvent("download");
    await page
      .getByRole("region", { name: "Facturas", exact: true })
      .getByRole("button", { name: "Exportar CSV" })
      .click();
    const csv = await readFile((await (await download).path()) ?? "", "utf8");
    const [, ...rows] = csv
      .replace(/^\uFEFF/, "")
      .trimEnd()
      .split("\r\n");
    expect(rows).toHaveLength(2);
    for (const row of rows) expect(row.split(",").at(-1)).not.toBe("");
  });

  expect(problems.list, problems.list.join("\n")).toEqual([]);
});

test("a visitor who opens /proveedores before setting a company up is told they are in the demo", async ({
  browser,
}) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  const problems = watch(page);

  await page.goto("/proveedores");

  await expect(page.getByText(/Estás en la empresa de demostración/)).toBeVisible();
  await expect(page.getByRole("main").getByRole("link", { name: "Usar con mi empresa" })).toHaveAttribute(
    "href",
    "/empezar",
  );
  expect(problems.list, problems.list.join("\n")).toEqual([]);
  await context.close();
});
