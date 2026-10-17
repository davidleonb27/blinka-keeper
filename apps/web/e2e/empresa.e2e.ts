import { expect, test, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { watch } from "./problems";

/**
 * A real company from the landing to its first decided invoices, against the real API: «Usar con mi empresa», the
 * set-up (profile, suppliers from a CSV, policy), the empty panel of a real workspace, the upload of its own invoices
 * (files and a pasted email), the decision and the CSV export. Zero console errors and zero failed requests.
 */

const SHOTS = path.resolve(__dirname, "../../../docs/lanes/reports/L18");
const SUPPLIERS_CSV = [
  "Distribuidora Andina SAS,900112334,Bancolombia,1204",
  "Nube Segura SAS,901554210,Davivienda,7781",
].join("\n");

const ANDINA = { name: "Distribuidora Andina SAS", taxId: "900112334", bank: "Bancolombia", account: "1204" };
const ESPIGA = { name: "Panadería La Espiga SAS", taxId: "900777123", bank: "Davivienda", account: "5566" };

function invoice(number: string, amount: string, supplier = ANDINA): string {
  return [
    `Proveedor: ${supplier.name}`,
    `Identificación tributaria: ${supplier.taxId}`,
    `Número de factura: ${number}`,
    "Fecha de emisión: 2026-10-15",
    `Monto: ${amount}`,
    "Moneda: USD",
    `Banco: ${supplier.bank}`,
    `Cuenta: ${supplier.account}`,
    "Concepto: Insumos de octubre",
  ].join("\n");
}

async function setUpCompany(page: Page) {
  await expect(page.getByRole("heading", { level: 1, name: "¿Cómo se llama tu empresa?" })).toBeVisible();
  await page.getByLabel("Nombre de la empresa").fill("Panadería El Trigal");
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText("¿Cómo se llama tu empresa?");
  await page.getByRole("button", { name: "Se ve bien" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "País, moneda y saldo" })).toBeVisible();
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.getByRole("heading", { level: 1, name: /Quién aprueba/ })).toBeVisible();
  await page.getByLabel("Nombre de quien aprueba").first().fill("Ana Gómez");
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Tus reglas, en tus palabras",
    }),
  ).toBeVisible();
  await page.getByLabel("Reglas").fill("Nada sobre 1500 dólares sin aprobación");
  await expect(page.getByRole("listitem").getByText(/Tope de aprobación automática/)).toBeVisible();
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "¿A quién le pagas?" })).toBeVisible();
  await page.locator('input[type="file"]').setInputFiles({
    name: "proveedores.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(SUPPLIERS_CSV),
  });
  await expect(page.getByRole("region", { name: "Beneficiarios importados" })).toContainText("Nube Segura SAS");
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Tu primera semana, decidida",
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Custodio está listo" })).toBeVisible();
  await page.getByRole("link", { name: /Ir al panel/ }).click();
}

test("a real company sets up, uploads its own invoices, decides them and exports the list", async ({ page }, info) => {
  const wide = info.project.name === "bogota";
  const width = wide ? 1440 : 390;
  await page.setViewportSize({ width, height: wide ? 900 : 844 });
  const problems = watch(page);
  const shot = (name: string) =>
    page.screenshot({
      path: path.join(SHOTS, `${name}-${width}.png`),
      fullPage: true,
    });

  await test.step("inicio: «Usar con mi empresa» lleva a /empezar", async () => {
    await page.goto("/");
    const entry = page.getByRole("main").getByRole("link", { name: "Usar con mi empresa" });
    await expect(entry).toBeVisible();
    await shot("landing");
    await entry.click();
    await expect(page).toHaveURL(/\/empezar$/);
  });

  await test.step("empezar: perfil, proveedores y política crean un espacio real que termina en el panel", async () => {
    await setUpCompany(page);
    await expect(page.getByRole("heading", { level: 1, name: "Panel" })).toBeVisible();
    const workspace = (await page.context().cookies()).find((cookie) => cookie.name === "custodio_ws")?.value ?? "";
    const summary = await page.request.get("/api/v1/workspaces/current", {
      headers: { "X-Custodio-Workspace": workspace },
    });
    expect(await summary.json()).toMatchObject({
      company_name: "Panadería El Trigal",
      pending_invoices: 0,
    });
  });

  await test.step("panel vacío: invita a subir facturas y el menú vuelve a /empezar", async () => {
    await expect(
      page.getByRole("heading", {
        name: "Aún no hay facturas: súbelas o reenvíalas",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("navigation", { name: "Secciones" }).getByRole("link", { name: "Usar con mi empresa" }),
    ).toHaveAttribute("href", "/empezar");
    await page.waitForLoadState("networkidle");
    await shot("panel-vacio");
  });

  await test.step("subir: archivos y un correo pegado, con avance y errores por archivo", async () => {
    await page
      .getByRole("region", {
        name: "Aún no hay facturas: súbelas o reenvíalas",
      })
      .getByRole("button", { name: "Subir facturas" })
      .click();
    const dialog = page.getByRole("dialog", { name: "Subir facturas" });
    await expect(dialog).toContainText("sólo a tus 2 proveedores registrados");
    await dialog.locator('input[type="file"]').setInputFiles([
      {
        name: "DA-501.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from(invoice("DA-501", "800.00")),
      },
      {
        name: "DA-502.eml",
        mimeType: "message/rfc822",
        buffer: Buffer.from(`From: cobros@andina.co\n\n${invoice("DA-502", "950.00")}`),
      },
      {
        name: "gastos.xlsx",
        mimeType: "application/vnd.ms-excel",
        buffer: Buffer.from("xlsx"),
      },
    ]);
    await dialog.getByLabel("O pega el texto de un correo con la factura").fill(invoice("DA-503", "2400.00"));
    await dialog.getByRole("button", { name: "Enviar el texto" }).click();
    const progress = dialog.getByRole("list", { name: "Avance de la subida" });
    await expect(progress.getByRole("listitem")).toHaveCount(4);
    await expect(progress.getByText("Recibida")).toHaveCount(3);
    await expect(progress.getByRole("listitem").filter({ hasText: "gastos.xlsx" })).toContainText(
      "Sólo leemos PDF, PNG, JPEG, WEBP, .eml o .txt.",
    );
    const decide = dialog.getByRole("button", { name: "Decidir 3 facturas" });
    await expect(decide).toBeVisible();
    await shot("subir");
    await decide.click();
    await expect(page.getByText("Custodio decidió 3 facturas.")).toBeVisible();
    await expect(dialog).toHaveCount(0);
  });

  await test.step("exportar: el CSV trae proveedor, número, monto, moneda, estado, regla, fecha y transferencia", async () => {
    const list = page.getByRole("region", { name: "Facturas", exact: true });
    await expect(list.getByRole("listitem")).toHaveCount(3);
    const download = page.waitForEvent("download");
    await list.getByRole("button", { name: "Exportar CSV" }).click();
    const csv = await readFile((await (await download).path()) ?? "", "utf8");
    const [header, ...rows] = csv.replace(/^﻿/, "").trimEnd().split("\r\n");
    expect(header).toBe("proveedor,numero,monto,moneda,estado,regla_decisiva,fecha,id_transferencia");
    expect(rows.map((row) => row.split(",").slice(0, 4).join(","))).toEqual(
      expect.arrayContaining([
        "Distribuidora Andina SAS,DA-501,800,USD",
        "Distribuidora Andina SAS,DA-502,950,USD",
        "Distribuidora Andina SAS,DA-503,2400,USD",
      ]),
    );
    await page.waitForLoadState("networkidle");
    await shot("panel");
  });

  await test.step("proveedor desconocido: su acta enlaza a «Agregar proveedores»", async () => {
    const list = page.getByRole("region", { name: "Facturas", exact: true });
    await list.getByRole("button", { name: "Subir facturas" }).click();
    const dialog = page.getByRole("dialog", { name: "Subir facturas" });
    await dialog.locator('input[type="file"]').setInputFiles([
      { name: "DA-504.pdf", mimeType: "application/pdf", buffer: Buffer.from(invoice("DA-504", "500.00")) },
      { name: "LE-77.pdf", mimeType: "application/pdf", buffer: Buffer.from(invoice("LE-77", "300.00", ESPIGA)) },
    ]);
    await dialog.getByRole("button", { name: "Decidir 2 facturas" }).click();
    await expect(page.getByText("Custodio decidió 2 facturas.")).toBeVisible();
    await list.getByRole("link", { name: new RegExp(ESPIGA.name) }).click();
    const acta = page.getByRole("dialog");
    await expect(acta).toContainText(`${ESPIGA.name} no está entre tus proveedores registrados`);
    await acta.getByRole("link", { name: "Agregar proveedores" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Proveedores" })).toBeVisible();
  });

  await test.step("proveedores: CSV y a mano, con vista previa; los registrados no cambian", async () => {
    const workspace = (await page.context().cookies()).find((cookie) => cookie.name === "custodio_ws")?.value ?? "";
    const headers = { "X-Custodio-Workspace": workspace };
    const before = await (await page.request.get("/api/v1/policy", { headers })).json();
    await page.locator('input[type="file"]').setInputFiles({
      name: "mas-proveedores.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(
        ["Nube Segura SAS,901554210,Bancolombia,0000", "Transportes El Cóndor,800443981,Banco de Bogotá,3390"].join(
          "\n",
        ),
      ),
    });
    const preview = page.getByRole("region", { name: "Vista previa de los cambios" });
    await expect(preview).toContainText("Transportes El Cóndor");
    await expect(preview.getByRole("listitem").filter({ hasText: "Nube Segura SAS" })).toContainText(
      "Ya está registrado",
    );
    const form = page.getByRole("form", { name: "Agregar a mano" });
    await form.getByLabel("Nombre").fill(ESPIGA.name);
    await form.getByLabel("NIT o identificación tributaria").fill(ESPIGA.taxId);
    await form.getByLabel("Banco").fill(ESPIGA.bank);
    await form.getByLabel("Cuenta, como aparece en sus facturas").fill(ESPIGA.account);
    await form.getByRole("button", { name: "Añadir a la vista previa" }).click();
    await expect(preview).toContainText(ESPIGA.name);
    await shot("proveedores");
    await preview.getByRole("button", { name: "Agregar 2 proveedores" }).click();
    await expect(
      page.getByText(`Se agregaron 2 proveedores. La política v${before.version + 1} quedó en el registro.`),
    ).toBeVisible();
    const after = await (await page.request.get("/api/v1/policy", { headers })).json();
    expect(after.beneficiaries.slice(0, before.beneficiaries.length)).toEqual(before.beneficiaries);
    expect(after.beneficiaries.map((b: { name: string }) => b.name)).toEqual(
      expect.arrayContaining(["Transportes El Cóndor", ESPIGA.name]),
    );
    const ledger = await (await page.request.get("/api/v1/ledger", { headers })).json();
    expect(ledger.at(-1)).toMatchObject({ kind: "policy_changed" });
  });

  await test.step("volver a decidir: la próxima factura del proveedor agregado ya lo reconoce", async () => {
    await page.goto("/panel");
    const list = page.getByRole("region", { name: "Facturas", exact: true });
    await list.getByRole("button", { name: "Subir facturas" }).click();
    const dialog = page.getByRole("dialog", { name: "Subir facturas" });
    await expect(dialog).toContainText("sólo a tus 4 proveedores registrados");
    await dialog.getByLabel("O pega el texto de un correo con la factura").fill(invoice("LE-78", "300.00", ESPIGA));
    await dialog.getByRole("button", { name: "Enviar el texto" }).click();
    await dialog.getByRole("button", { name: "Decidir 1 factura" }).click();
    await expect(page.getByText("Custodio decidió 1 factura.")).toBeVisible();
    const workspace = (await page.context().cookies()).find((cookie) => cookie.name === "custodio_ws")?.value ?? "";
    const decisions = await (
      await page.request.get("/api/v1/decisions", { headers: { "X-Custodio-Workspace": workspace } })
    ).json();
    const byNumber = (n: string) => decisions.find((d: { invoice_number: string }) => d.invoice_number === n).decision;
    expect(byNumber("LE-77").beneficiary_id).toBeNull();
    expect(byNumber("LE-78").beneficiary_id).not.toBeNull();
    expect(byNumber("LE-77").status).not.toMatch(/^paid/);
    await expect(list.getByRole("listitem")).toHaveCount(6);
    const download = page.waitForEvent("download");
    await list.getByRole("button", { name: "Exportar CSV" }).click();
    const csv = await readFile((await (await download).path()) ?? "", "utf8");
    expect(csv).toContain(`${ESPIGA.name},LE-78,300,USD`);
  });

  expect(problems.list, problems.list.join("\n")).toEqual([]);
});
