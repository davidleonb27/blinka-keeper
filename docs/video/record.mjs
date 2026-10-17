// Records the pitch's product takes on the deployed demo, in a brand-new demo workspace.
// Usage: node record.mjs [outDir] [take ...]   (default outDir: build/raw; default: every take, in order)
//        node record.mjs --real [outDir] [block ...]   «mouse real» takes for GUION-VOZ.md (default outDir: build/real)
// Each take writes build/raw/<take>.mp4 (30 fps) and <take>.marks.json; edl.json cuts the pitch from those marks.
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import {
  SCALE, VIEWPORT, clickLocator, moveTo, moveToLocator, preparePage, restoreCursor, smoothScroll, smoothScrollInto,
  startRecording, union, zoomOut, zoomTo,
} from "./lib.mjs";
import { BLOCKS as REAL_BLOCKS, ORDER as REAL_ORDER } from "./real.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.CUSTODIO_URL ?? "https://custodio-blinka-green.vercel.app";
const REAL = process.argv[2] === "--real";
const ARGS = process.argv.slice(REAL ? 3 : 2);
const OUT = path.resolve(ARGS[0] ?? path.join(HERE, "build", REAL ? "real" : "raw"));
const ONLY = ARGS.slice(1);
const ATTACK_PDF = path.join(OUT, "factura-AC-2026-14.pdf");
const RULE = "Nada sobre 1.000 USD sin que lo apruebe Ana";
const LONG = { timeout: 240_000 };

const hold = (page, ms) => page.waitForTimeout(ms);

async function open(page, url) {
  page.__camera = null;
  await page.goto(BASE + url);
  await page.waitForLoadState("networkidle");
  await restoreCursor(page);
  await hold(page, 500);
}

async function search(page, text) {
  const box = page.getByPlaceholder("Buscar proveedor o número");
  await clickLocator(page, box, 600);
  await box.fill("");
  await page.keyboard.type(text, { delay: 55 });
  await hold(page, 700);
}

async function openRow(page, text) {
  const row = page.getByRole("region", { name: "Facturas" }).getByRole("link").filter({ hasText: text }).first();
  await clickLocator(page, row);
  const acta = page.getByRole("dialog");
  await acta.waitFor();
  await hold(page, 900);
  return acta;
}

async function closeActa(page) {
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "detached" });
  await hold(page, 400);
}

const TAKES = {
  // Landing → brand-new demo workspace → 36 invoices decided → the panel's measured figures.
  async landing(page, rec) {
    await open(page, "/");
    rec.mark("hero");
    await hold(page, 1800);
    await clickLocator(page, page.getByRole("link", { name: /Probar con una empresa demo/ }).first(), 900);
    rec.mark("click_demo");
    await page.waitForURL(/\/panel/);
    await page.getByRole("button", { name: /Decidir las \d+ facturas/ }).waitFor(LONG);
    await page.waitForLoadState("networkidle");
    rec.mark("panel");
    await hold(page, 1200);
    const banner = page.getByRole("region", { name: "Facturas por decidir" });
    await zoomTo(page, await banner.boundingBox(), 1.35);
    rec.mark("zoom_inbox");
    await hold(page, 1600);
    await zoomOut(page);
    await clickLocator(page, banner.getByRole("button", { name: /Decidir las \d+ facturas/ }));
    rec.mark("decide_click");
    await page.getByText(/Custodio decidió \d+ facturas/).waitFor(LONG);
    rec.mark("decided");
    await moveTo(page, 1250, 980, 600);
    await hold(page, 1500);
    const overview = page.getByRole("region", { name: "Resumen" });
    const zeroCard = overview.getByText("Pagos indebidos").locator("xpath=ancestor::*[contains(@class,'card-surface')][1]");
    await zoomTo(page, await zeroCard.boundingBox(), 1.45);
    rec.mark("zoom_zero");
    await hold(page, 2600);
    await zoomOut(page);
    const cards = ["Pagado", "Retenido", "Pendiente"].map((name) => page.getByText(name, { exact: true }).first());
    const boxes = await Promise.all(cards.map((c) => c.locator("xpath=ancestor::*[contains(@class,'card-surface')][1]").boundingBox()));
    await zoomTo(page, union(...boxes), 1.3);
    rec.mark("zoom_counts");
    await hold(page, 2600);
    await zoomOut(page);
    rec.mark("end");
  },

  // A held invoice with a changed account sent from a look-alike domain: why, who to call (the contact on file), the
  // OFAC check and the out-of-band rule.
  async held(page, rec) {
    await open(page, "/panel");
    await clickLocator(page, page.getByRole("button", { name: /^Retenidas/ }));
    await search(page, "Joaquín Méndez");
    const acta = await openRow(page, "Joaquín Méndez");
    rec.mark("acta");
    await hold(page, 900);
    const why = acta.getByText("Por qué", { exact: true });
    const changeText = acta.getByText("Qué tendría que cambiar", { exact: true }).locator("xpath=following-sibling::*[1]");
    await zoomTo(page, union(await why.boundingBox(), await changeText.boundingBox()), 1.35);
    rec.mark("zoom_why");
    await hold(page, 5200);
    await zoomOut(page);
    const r14 = acta.getByRole("listitem").filter({ hasText: "Sin coincidencia en la lista OFAC" });
    const r15 = acta.getByRole("listitem").filter({ hasText: "Verificación fuera de banda" });
    await smoothScrollInto(page, r14, 160);
    await hold(page, 400);
    await zoomTo(page, union(await r14.boundingBox(), await r15.boundingBox()), 1.45);
    rec.mark("zoom_controls");
    await hold(page, 4600);
    await zoomOut(page);
    await closeActa(page);
    rec.mark("end");
  },

  // A paid invoice whose transfer already went out: the Stripe test-mode id in the acta. Payments not yet due wait for
  // their day (the scheduler), so the take asks the API which one carries a tr_ id.
  async paid(page, rec) {
    const workspace = (await page.context().cookies()).find((c) => c.name === "custodio_ws")?.value ?? "";
    const response = await page.request.get(`${BASE}/api/v1/decisions`, { headers: { "X-Custodio-Workspace": workspace } });
    const body = await response.json();
    const sent = (body.items ?? body).find((item) => /^tr_/.test(JSON.stringify(item).match(/"external_id":"([^"]*)"/)?.[1] ?? ""));
    if (!sent) throw new Error("ningún pago de este espacio salió por Stripe (¿tope diario de transferencias de prueba?)");
    const supplier = sent.decision.supplier_name;
    console.log(`[paid] con transferencia: ${sent.decision.invoice_id} ${supplier}`);
    await open(page, "/panel");
    await clickLocator(page, page.getByRole("button", { name: /^Pagadas/ }));
    await search(page, supplier);
    const acta = await openRow(page, supplier);
    rec.mark("acta");
    const payment = acta.getByRole("region", { name: "Ejecución del pago" });
    await smoothScrollInto(page, payment, 200, 600);
    await moveToLocator(page, payment.getByText(/tr_/), 900);
    await zoomTo(page, await payment.boundingBox(), 1.8);
    rec.mark("zoom_tr");
    await hold(page, 3800);
    await zoomOut(page);
    await closeActa(page);
    rec.mark("end");
  },

  // The scheduler: approved payments go out on their due date, never under the reserve, with the value it captures.
  async calendar(page, rec) {
    await open(page, "/calendario");
    await page.getByText("Valor capturado este mes").waitFor(LONG);
    rec.mark("start");
    await hold(page, 1500);
    const value = page.getByText("Valor capturado este mes").locator("xpath=ancestor::*[contains(@class,'card-surface')][1]");
    await zoomTo(page, await value.boundingBox(), 1.5);
    rec.mark("zoom_value");
    await hold(page, 2800);
    await zoomOut(page);
    const next = page.getByRole("region", { name: "Próximos 45 días" });
    const box = await next.boundingBox();
    await zoomTo(page, { ...box, height: Math.min(box.height, 330) }, 1.45);
    rec.mark("zoom_next");
    await hold(page, 3000);
    await zoomOut(page);
    rec.mark("end");
  },

  // Bank reconciliation with the demo statement. The camera frames the page below the upload hint (which names the
  // model that reads PDF statements) from the first cut frame on.
  async reconcile(page, rec) {
    await open(page, "/conciliacion");
    const button = page.getByRole("button", { name: /Usar extracto de demo/ });
    await button.waitFor(LONG);
    const hint = await page.getByText(/CSV: lo lee el código/).boundingBox();
    const top = hint.y + hint.height + 6;
    await moveToLocator(page, button, 600);
    await zoomTo(page, { x: 0, y: top, width: 1920, height: 1080 - top }, 1080 / (1080 - top), 700);
    rec.mark("framed");
    await hold(page, 600);
    await clickLocator(page, button);
    rec.mark("demo_click");
    const heading = page.getByText(/Extracto de \w+ de \d{4}/);
    await heading.waitFor(LONG);
    rec.mark("reconciled");
    await hold(page, 900);
    const summary = union(await heading.boundingBox(), await page.getByText("Aún no en el banco").first().boundingBox());
    await zoomTo(page, { ...summary, x: summary.x - 20, width: summary.width + 900, height: summary.height + 80 }, 1.35);
    rec.mark("zoom_summary");
    await hold(page, 3400);
    const alerts = page.getByText("Sin factura", { exact: true }).first();
    await zoomTo(page, { ...(await alerts.boundingBox()), width: 420, height: 160 }, 1.9);
    rec.mark("zoom_unbilled");
    await hold(page, 2400);
    rec.mark("end");
    await zoomOut(page);
  },

  // Earned autonomy: «Simular 30 días» plays a seeded month; a single risk signal sends a supplier back to supervision.
  async autonomy(page, rec) {
    await open(page, "/autonomia");
    const simulate = page.getByRole("button", { name: /Simular 30 días/ });
    await simulate.waitFor(LONG);
    rec.mark("start");
    await hold(page, 900);
    await clickLocator(page, simulate);
    rec.mark("simulate_click");
    const done = page.getByText(/^Simulado: 30 días/);
    await done.waitFor(LONG);
    rec.mark("simulated");
    await hold(page, 900);
    await zoomTo(page, union(await done.boundingBox(), await page.getByText("Tasa de autonomía").boundingBox()), 1.35);
    rec.mark("zoom_simulated");
    await hold(page, 3000);
    await zoomOut(page);
    const card = page.getByText("Confianza revocada", { exact: false }).first().locator("xpath=ancestor::*[contains(@class,'card-surface')][1]");
    await card.scrollIntoViewIfNeeded();
    await zoomTo(page, await card.boundingBox(), 1.6);
    rec.mark("zoom_revoked");
    await hold(page, 3200);
    await zoomOut(page);
    rec.mark("end");
  },

  // Outside the agreement → waits for a person → Ana approves → paid on the rail, approval in the ledger.
  async approve(page, rec) {
    await open(page, "/panel");
    await clickLocator(page, page.getByRole("button", { name: /Esperan aprobación/ }));
    await search(page, "Cumulus");
    const acta = await openRow(page, "1.300");
    rec.mark("acta");
    const why = acta.getByText("Por qué", { exact: true });
    await zoomTo(page, union(await why.boundingBox(), await why.locator("xpath=following-sibling::*[1]").boundingBox()), 1.5);
    rec.mark("zoom_why");
    await hold(page, 3200);
    await zoomOut(page);
    const approve = acta.getByRole("button", { name: /Aprobar pago/ });
    await moveToLocator(page, approve, 900);
    await zoomTo(page, union(await approve.boundingBox(), await acta.getByText("Decides como").boundingBox()), 1.4);
    rec.mark("zoom_approve");
    await hold(page, 1200);
    await zoomOut(page, 600);
    await clickLocator(page, approve, 300);
    rec.mark("approve_click");
    await acta.getByText(/Aprobada por .+ · /).waitFor(LONG);
    rec.mark("approved");
    await hold(page, 800);
    await smoothScrollInto(page, acta.getByText("Ejecución del pago", { exact: true }), 140, 600);
    const payment = acta.getByRole("region", { name: "Ejecución del pago" });
    await zoomTo(page, await payment.boundingBox(), 1.7);
    rec.mark("zoom_tr");
    await hold(page, 3200);
    await zoomOut(page);
    await closeActa(page);
    rec.mark("end");
  },

  // The hash chain: verify (green), then tamper with a copy (red, at the exact entry).
  async ledger(page, rec) {
    await open(page, "/registro");
    rec.mark("start");
    await clickLocator(page, page.getByRole("button", { name: /Verificar la cadena/ }));
    await page.getByText(/La cadena está íntegra/).waitFor(LONG);
    rec.mark("verified");
    await zoomTo(page, await page.getByText(/La cadena está íntegra/).boundingBox(), 1.6);
    rec.mark("zoom_verified");
    await hold(page, 2600);
    await zoomOut(page);
    await clickLocator(page, page.getByRole("button", { name: /Alterar una copia/ }));
    await page.getByText(/se rompe en el asiento/).waitFor(LONG);
    rec.mark("tampered");
    await hold(page, 600);
    const broken = page.getByText(/se rompe en el asiento/);
    const row = page.getByText("alterado en la copia").locator("xpath=ancestor::li[1]");
    await zoomTo(page, union(await broken.boundingBox(), await row.boundingBox()), 1.3);
    rec.mark("zoom_tampered");
    await hold(page, 3600);
    await zoomOut(page);
    rec.mark("end");
  },

  // A rule in plain Spanish → compiled → simulated against the month before applying.
  async rules(page, rec) {
    await open(page, "/reglas");
    const field = page.getByLabel("Regla en español");
    await clickLocator(page, field);
    rec.mark("typing");
    await page.keyboard.type(RULE, { delay: 50 });
    rec.mark("typed");
    await hold(page, 500);
    await clickLocator(page, page.getByRole("button", { name: /Compilar y simular/ }));
    rec.mark("compile_click");
    const understood = page.getByRole("heading", { name: "Así lo entendió Custodio" });
    await understood.waitFor(LONG);
    rec.mark("compiled");
    await hold(page, 800);
    const card = understood.locator("xpath=ancestor::*[contains(@class,'card-surface')][1]");
    await zoomTo(page, await card.boundingBox(), 1.6);
    rec.mark("zoom_understood");
    await hold(page, 2600);
    await zoomOut(page);
    const before = page.getByRole("region", { name: "Antes de aplicar" });
    const box = await before.boundingBox();
    await zoomTo(page, { ...box, height: Math.min(box.height, 520) }, 1.45);
    rec.mark("zoom_simulation");
    await hold(page, 3200);
    await zoomOut(page);
    rec.mark("end");
  },

  // A real trap PDF (white-on-white order + changed account) uploaded to the public challenge.
  async attack(page, rec) {
    execFileSync("uv", ["run", "--directory", path.join(HERE, "../../apps/api"), "python", path.join(HERE, "make_attack_pdf.py"), ATTACK_PDF], {
      env: { ...process.env, PYTHONPATH: path.join(HERE, "../../apps/api") },
      stdio: "inherit",
    });
    await open(page, "/reto");
    rec.mark("start");
    const upload = page.getByText(/O sube un PDF o una imagen/);
    await moveToLocator(page, upload, 900);
    await page.locator('input[type="file"]').setInputFiles(ATTACK_PDF);
    rec.mark("file");
    await hold(page, 1200);
    await clickLocator(page, page.getByRole("button", { name: /Intentar que pague/ }));
    rec.mark("submit");
    const result = page.getByRole("region", { name: "Resultado de tu intento" });
    await result.waitFor(LONG);
    rec.mark("result");
    await hold(page, 700);
    const top = await result.evaluate((el) => el.getBoundingClientRect().top + scrollY);
    await smoothScroll(page, top - 90, 900);
    await hold(page, 400);
    await zoomTo(page, await result.boundingBox(), 1.3);
    rec.mark("zoom_result");
    await hold(page, 5200);
    await zoomOut(page);
    await smoothScroll(page, 0, 900);
    const counter = page.getByRole("region", { name: "Contador global" });
    await zoomTo(page, await counter.boundingBox(), 1.5);
    rec.mark("zoom_counter");
    await hold(page, 3000);
    await zoomOut(page);
    rec.mark("end");
  },

  // The arena: an attacking model changes technique each round; the rules do not change. The camera frames the battle
  // below the page heading from the first cut frame to the last (the brief keeps model names out of the video).
  async arena(page, rec) {
    await open(page, "/arena");
    rec.mark("start");
    await clickLocator(page, page.getByRole("button", { name: /Empezar el ataque/ }));
    rec.mark("attack_click");
    const heading = await page.getByRole("heading", { level: 1 }).locator("xpath=following-sibling::*[1]").boundingBox();
    const top = heading.y + heading.height + 12;
    await zoomTo(page, { x: 0, y: top, width: 1920, height: 1080 - top }, 1080 / (1080 - top), 900);
    rec.mark("framed");
    await page.getByRole("button", { name: /Otra vez/ }).waitFor(LONG);
    rec.mark("done");
    await hold(page, 800);
    const stats = page.getByText("Pagos indebidos", { exact: true }).locator("xpath=ancestor::div[contains(@class,'grid-cols-3')][1]");
    await zoomTo(page, await stats.boundingBox(), 1.3);
    rec.mark("zoom_stats");
    await hold(page, 3000);
    rec.mark("end");
    await zoomOut(page);
  },

  // The public challenge on a stage: a QR to /reto and the improper-payments counter, live.
  async stage(page, rec) {
    await open(page, "/reto?escenario=1");
    const counter = page.getByRole("region", { name: "Contador en vivo" });
    await counter.waitFor(LONG);
    rec.mark("start");
    await hold(page, 2200);
    await zoomTo(page, await counter.boundingBox(), 1.35);
    rec.mark("zoom_counter");
    await hold(page, 2600);
    await zoomOut(page);
    rec.mark("end");
  },

  // Self-hosting in one command, as the open-source site documents it.
  async docs(page, rec) {
    await open(page, "/docs/inicio-rapido");
    const command = page.getByText("docker compose up --build").first();
    await command.waitFor(LONG);
    rec.mark("start");
    await hold(page, 1200);
    const block = command.locator("xpath=ancestor::*[self::pre or contains(@class,'rounded')][1]");
    await zoomTo(page, await block.boundingBox(), 1.6);
    rec.mark("zoom_docker");
    await hold(page, 3200);
    await zoomOut(page);
    rec.mark("end");
  },
};

// approve stays available. Since the scheduler (L13) an approved payment waits for its due date, so the cut shows the
// transfer of an invoice paid on its own (paid). The deployment caps Stripe test transfers per day; when the cap is hit,
// paid fails loudly and build.py falls back to a paid_stripe take recorded earlier, if there is one.
const ORDER = ["landing", "held", "paid", "ledger", "rules", "reconcile", "calendar", "autonomy", "attack", "arena", "stage", "docs"];

if (REAL) {
  await recordReal();
  process.exit(0);
}

async function recordReal() {
  mkdirSync(OUT, { recursive: true });
  const attack = path.join(OUT, "factura-AC-2026-14.pdf");
  execFileSync("uv", ["run", "--directory", path.join(HERE, "../../apps/api"), "python", path.join(HERE, "make_attack_pdf.py"), attack], {
    env: { ...process.env, PYTHONPATH: path.join(HERE, "../../apps/api") },
    stdio: "inherit",
  });
  mkdirSync(path.join(OUT, "..", "assets"), { recursive: true });
  execFileSync("pdftoppm", ["-r", "200", "-png", "-singlefile", attack, path.join(OUT, "..", "assets", "attack")]);
  const state = path.join(OUT, "state.json");
  const reuse = ONLY.length > 0 && !ONLY.includes("b03");
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: VIEWPORT, deviceScaleFactor: SCALE, locale: "es-CO", timezoneId: "America/Bogota", colorScheme: "light",
    ...(reuse ? { storageState: state } : {}),
  });
  const page = await preparePage(context);
  page.on("pageerror", (error) => console.log("pageerror", error.message));
  for (const block of REAL_ORDER.filter((name) => ONLY.length === 0 || ONLY.includes(name))) {
    const act = await REAL_BLOCKS[block](page, { base: BASE, here: HERE, out: OUT });
    const rec = await startRecording(page, OUT, block);
    await act(rec);
    const { list, frames, end } = await rec.stop();
    if (block === "b03") await context.storageState({ path: state });
    console.log(`${block}: ${frames} cuadros en ${end.toFixed(1)} s`);
    execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", list, "-vf", "fps=30,format=yuv420p",
      "-c:v", "libx264", "-preset", "medium", "-crf", "16", path.join(OUT, `${block}.mp4`)]);
  }
  await browser.close();
}

// Without the landing take, reuse the demo workspace the last full run created (handy to re-record one take).
const STATE = path.join(OUT, "state.json");
const reuse = ONLY.length > 0 && !ONLY.includes("landing");

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: VIEWPORT, deviceScaleFactor: SCALE, locale: "es-CO", timezoneId: "America/Bogota", colorScheme: "light",
  ...(reuse ? { storageState: STATE } : {}),
});
const page = await preparePage(context);
page.on("pageerror", (error) => console.log("pageerror", error.message));
for (const take of ORDER.filter((name) => ONLY.length === 0 || ONLY.includes(name))) {
  const rec = await startRecording(page, OUT, take);
  try {
    await TAKES[take](page, rec);
  } catch (error) {
    if (take !== "paid") throw error;
    console.log(`paid: ${error.message}; se omite la toma`);
    await rec.stop();
    continue;
  }
  const { list, frames, end } = await rec.stop();
  if (take === "landing") await context.storageState({ path: STATE });
  console.log(`${take}: ${frames} frames in ${end.toFixed(1)} s (${(frames / end).toFixed(1)} fps captured)`);
  execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", list, "-vf", "fps=30,format=yuv420p",
    "-c:v", "libx264", "-preset", "medium", "-crf", "16", path.join(OUT, `${take}.mp4`)]);
}
await browser.close();
