// «Mouse real» takes for the voice-over demo (docs/video/GUION-VOZ.md): one continuous take per block, at human pace,
// with no speed-up and no cut inside a block. Each take starts from a ready state (prepared off camera), leaves named
// marks the edit syncs to the voice, and ends with a few seconds of idle hand so the edit can wait without freezing.
import { execFileSync } from "node:child_process";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { humanClick, humanHover, humanMove, humanScroll, humanScrollTo, humanType, idle, restoreCursor } from "./lib.mjs";

const TAIL = 4500; // idle hand after the last action
const LONG = { timeout: 240_000 };
const RULE = "Nada sobre 3000 dólares sin aprobación";
const NOTE = "Revisado con el banco: no corresponde a ninguna factura.";
const REVIEWER = "Ana Gómez";

/** The words of the attack PDF with their boxes (points, top-left), and which ones it draws white on white. */
function pdfWords(pdf) {
  const xml = execFileSync("pdftotext", ["-bbox", pdf, "-"], { encoding: "utf8" });
  const words = [...xml.matchAll(/xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</g)].map((m) => ({
    x0: +m[1], y0: +m[2], x1: +m[3], y1: +m[4], text: m[5],
  }));
  const first = words.findIndex((w) => w.text === "Nota");
  const last = words.findIndex((w, i) => i > first && w.text === "revisión.");
  words.forEach((w, i) => { w.hidden = i >= first && i <= last; });
  words[first].id = "hidden-first";
  words[last].id = "hidden-last";
  words.find((w) => w.text === "Banco:").id = "account-first";
  return words;
}

async function ready(page, base, url) {
  page.__camera = null;
  await page.goto(base + url);
  await page.waitForLoadState("networkidle");
  await restoreCursor(page);
  await page.waitForTimeout(600);
}

export const ORDER = ["b01", "b03", "b04", "b05", "b06", "b08", "b09", "b07", "b10"];

export const BLOCKS = {
  // 1 · The trap PDF: selecting the blank band reveals the order written white on white, then the changed account.
  async b01(page, { here, out }) {
    const pdf = path.join(out, "factura-AC-2026-14.pdf");
    const png = path.join(out, "..", "assets", "attack.png");
    await page.goto(pathToFileURL(path.join(here, "pdf.html")).href);
    await page.evaluate((data) => window.load(data), {
      image: pathToFileURL(png).href, width: 612, height: 792, words: pdfWords(pdf), scale: 1.6,
    });
    await restoreCursor(page);
    await page.waitForTimeout(500);
    return async (rec) => {
      await humanHover(page, page.locator("#page"), 1400);
      const first = await page.locator("#hidden-first").boundingBox();
      const last = await page.locator("#hidden-last").boundingBox();
      await humanMove(page, first.x + 2, first.y + first.height / 2);
      await page.waitForTimeout(450);
      rec.mark("select_hidden");
      await page.mouse.down();
      // Inside the last word: released past it, the browser would anchor the selection at the top of the page.
      await humanMove(page, last.x + last.width * 0.92, last.y + last.height / 2);
      await page.mouse.up();
      rec.mark("hidden_revealed");
      await page.waitForTimeout(1800);
      const account = await page.locator("#account-first").boundingBox();
      await humanMove(page, account.x + 2, account.y + account.height / 2);
      await page.waitForTimeout(400);
      await page.keyboard.down("Shift");
      await page.mouse.down();
      await page.mouse.up();
      await page.keyboard.up("Shift");
      rec.mark("account_selected");
      await idle(page, TAIL);
    };
  },

  // 3 · A brand-new demo company: 38 invoices decided with one click; the cursor points at the panel's figures.
  async b03(page, { base }) {
    await ready(page, base, "/");
    return async (rec) => {
      await page.waitForTimeout(900);
      await humanClick(page, page.getByRole("link", { name: /Probar con una empresa demo/ }).first());
      rec.mark("demo_click");
      const decide = page.getByRole("button", { name: /Decidir las \d+ facturas/ });
      await decide.waitFor(LONG);
      rec.mark("panel");
      await humanHover(page, page.getByRole("region", { name: "Facturas por decidir" }).getByText(/facturas recibidas/), 900);
      await humanClick(page, decide);
      rec.mark("decide_click");
      const done = page.getByText(/Custodio decidió \d+ facturas/);
      while (!(await done.isVisible().catch(() => false))) await idle(page, 900);
      rec.mark("decided");
      for (const name of ["Pagado", "Retenido", "Pendiente"]) await humanHover(page, page.getByText(name, { exact: true }).first(), 1100);
      await humanHover(page, page.getByRole("region", { name: "Resumen" }).getByText("Pagos indebidos"), 600);
      rec.mark("zero");
      await humanHover(page, page.getByRole("region", { name: "Resumen" }).getByText(/^0$/).first(), 1600);
      await idle(page, TAIL);
    };
  },

  // 4 · The trap PDF uploaded to «Róbale a Custodio»: FRENADO, and the rules that stopped it with their reasons.
  async b04(page, { base, out }) {
    await ready(page, base, "/reto");
    return async (rec) => {
      const drop = page.getByText(/O sube un PDF o una imagen/);
      await humanHover(page, drop, 500);
      const [chooser] = await Promise.all([page.waitForEvent("filechooser"), humanClick(page, drop)]);
      await chooser.setFiles(path.join(out, "factura-AC-2026-14.pdf"));
      rec.mark("file");
      await page.waitForTimeout(700);
      await humanClick(page, page.getByRole("button", { name: /Intentar que pague/ }));
      rec.mark("submit");
      const result = page.getByRole("region", { name: "Resultado de tu intento" });
      while (!(await result.isVisible().catch(() => false))) await idle(page, 700);
      rec.mark("result");
      await humanScrollTo(page, result, 120);
      await humanHover(page, result.getByText(/FRENADO|ESCALADO|PAGADO|PAGO INDEBIDO/).first(), 1500);
      // The result lists the rules that fired with their reasons; its «Ver el acta» link does not load in production
      // (the challenge decides in its own sandbox), so the take reads the rules here.
      rec.mark("acta");
      for (const rule of ["R2", "R4", "R15"]) {
        const row = result.getByText(new RegExp(`^${rule} · `)).first();
        await humanScrollTo(page, row, 300);
        await humanHover(page, row, 1700);
        rec.mark(`rule_${rule.toLowerCase()}`);
      }
      await idle(page, TAIL);
    };
  },

  // 5 · A paid invoice whose transfer went out by Stripe in test mode: the cursor rests on the tr_ id.
  async b05(page, { base }) {
    await ready(page, base, "/panel");
    const workspace = (await page.context().cookies()).find((c) => c.name === "custodio_ws")?.value ?? "";
    const decisions = await (await page.request.get(`${base}/api/v1/decisions`, { headers: { "X-Custodio-Workspace": workspace } })).json();
    const sent = decisions.find((item) => /^tr_/.test(item.decision.execution?.external_id ?? ""));
    if (!sent) console.log("b05: ningún pago salió por Stripe (¿tope diario de transferencias de prueba?); se graba una pagada sin tr_");
    const supplier = (sent ?? decisions.find((item) => item.decision.status === "paid_auto")).decision.supplier_name;
    return async (rec) => {
      await humanClick(page, page.getByRole("button", { name: /^Pagadas/ }));
      const row = page.getByRole("region", { name: "Facturas" }).getByRole("link").filter({ hasText: supplier }).first();
      await humanScrollTo(page, row, 420);
      await humanClick(page, row);
      const acta = page.getByRole("dialog");
      await acta.waitFor(LONG);
      rec.mark("acta");
      await page.waitForTimeout(900);
      const payment = acta.getByRole("region", { name: "Ejecución del pago" });
      await humanHover(page, acta.getByText("Por qué", { exact: true }), 500);
      await humanScrollTo(page, payment, 300);
      await humanHover(page, payment.getByText(/Stripe · modo prueba/), 1300);
      rec.mark("hover_tr");
      await humanHover(page, sent ? payment.getByText(/tr_/).first() : payment, 2600);
      await idle(page, TAIL);
    };
  },

  // 6 · A rule typed key by key, compiled and simulated before it is applied.
  async b06(page, { base }) {
    await ready(page, base, "/reglas");
    return async (rec) => {
      await humanClick(page, page.getByLabel("Regla en español"));
      rec.mark("typing");
      await humanType(page, RULE);
      await page.waitForTimeout(400);
      await humanClick(page, page.getByRole("button", { name: /Compilar y simular/ }));
      rec.mark("compile_click");
      const understood = page.getByRole("heading", { name: "Así lo entendió Custodio" });
      while (!(await understood.isVisible().catch(() => false))) await idle(page, 700);
      rec.mark("compiled");
      await humanHover(page, understood, 1400);
      const before = page.getByRole("region", { name: "Antes de aplicar" });
      await humanHover(page, before.getByText("Autonomía").first(), 1500);
      await humanHover(page, before.getByText(/Pagada sola/).first(), 1500);
      await idle(page, TAIL);
    };
  },

  // 8 · Bank reconciliation: the demo statement, the two alerts reviewed with a note, the month closed, the evidence.
  async b08(page, { base }) {
    await ready(page, base, "/conciliacion");
    // The upload hint names the model that reads PDF statements; the take starts scrolled just past it. The page is
    // short before a statement is loaded, so it gets room to scroll (nothing visible changes).
    const hint = await page.getByText(/CSV: lo lee el código/).boundingBox();
    await page.evaluate((y) => {
      document.body.style.minHeight = "300vh";
      scrollBy(0, y);
    }, hint.y + hint.height + 4);
    await page.waitForTimeout(400);
    return async (rec) => {
      await humanClick(page, page.getByRole("button", { name: /Usar extracto de demo/ }));
      rec.mark("demo_click");
      const summary = page.getByRole("region", { name: "Resumen de la conciliación" });
      while (!(await summary.isVisible().catch(() => false))) await idle(page, 700);
      rec.mark("reconciled");
      await humanHover(page, summary.getByText("Conciliado", { exact: true }).first(), 1500);
      const alerts = page.getByRole("region", { name: "Alertas" });
      await humanScrollTo(page, alerts, 140);
      rec.mark("alerts_view");
      await humanHover(page, alerts.getByText("Alertas", { exact: true }), 900);
      for (let i = 0; i < 2; i++) {
        const form = alerts.getByRole("form").first();
        if (!(await form.count())) break;
        await humanScrollTo(page, form, 260);
        await humanClick(page, form.getByLabel("Nota de revisión"));
        await humanType(page, NOTE);
        const who = form.getByLabel("Quién revisa");
        if (!(await who.inputValue())) {
          await humanClick(page, who);
          await humanType(page, REVIEWER);
        }
        await humanClick(page, form.getByRole("button", { name: /Marcar como revisado/ }));
        rec.mark(`reviewed_${i + 1}`);
        await page.waitForTimeout(1200);
      }
      const closing = page.getByRole("region", { name: "Cierre del mes" });
      await humanScrollTo(page, closing, 220);
      const closer = closing.getByLabel("Quién cierra");
      if (!(await closer.inputValue())) {
        await humanClick(page, closer);
        await humanType(page, REVIEWER);
      }
      await humanClick(page, closing.getByRole("button", { name: /Cerrar/ }));
      rec.mark("close_click");
      const closed = closing.getByText(/Mes cerrado por/);
      while (!(await closed.isVisible().catch(() => false))) await idle(page, 700);
      rec.mark("closed");
      const [download] = await Promise.all([
        page.waitForEvent("download", LONG),
        humanClick(page, closing.getByRole("button", { name: /Descargar el paquete/ })),
      ]);
      rec.mark("download");
      console.log(`b08: evidencia descargada: ${download.suggestedFilename()}`);
      await idle(page, TAIL);
    };
  },

  // 9 · The chain: verify (green), then tamper with a copy (red at the exact entry).
  async b09(page, { base }) {
    await ready(page, base, "/registro");
    return async (rec) => {
      await humanHover(page, page.getByRole("heading", { level: 1 }), 700);
      await humanClick(page, page.getByRole("button", { name: /Verificar la cadena/ }));
      const intact = page.getByText(/La cadena está íntegra/);
      await intact.waitFor(LONG);
      rec.mark("verified");
      await humanHover(page, intact, 1300);
      await humanClick(page, page.getByRole("button", { name: /Alterar una copia/ }));
      rec.mark("tamper_click");
      const broken = page.getByText(/se rompe en el asiento/);
      await broken.waitFor(LONG);
      rec.mark("tampered");
      await humanHover(page, broken, 1300);
      await humanHover(page, page.getByText("alterado en la copia"), 1500);
      await idle(page, TAIL);
    };
  },

  // 7 · Earned autonomy: «Simular 30 días», the chart and a supplier back under supervision, then the calendar.
  async b07(page, { base }) {
    await ready(page, base, "/autonomia");
    return async (rec) => {
      await humanHover(page, page.getByRole("heading", { level: 1 }), 600);
      await humanClick(page, page.getByRole("button", { name: /Simular 30 días/ }));
      rec.mark("simulate_click");
      const done = page.getByText(/^Simulado: 30 días/);
      while (!(await done.isVisible().catch(() => false))) await idle(page, 700);
      rec.mark("simulated");
      await humanHover(page, page.getByText("Tasa de autonomía"), 1000);
      await humanHover(page, page.getByText("Autonomía por día"), 1000);
      await humanHover(page, page.getByText("En supervisión").first(), 1100);
      await humanClick(page, page.getByRole("link", { name: "Calendario" }).first());
      const next = page.getByRole("region", { name: "Próximos 45 días" });
      await next.waitFor(LONG);
      rec.mark("calendar_open");
      await humanHover(page, next.getByText(/Se paga el|Se adelanta/).first(), 1800);
      await idle(page, TAIL);
    };
  },

  // 10 · The live challenge on a stage: the QR and the improper-payments counter.
  async b10(page, { base }) {
    await ready(page, base, "/reto?escenario=1");
    await page.getByRole("region", { name: "Contador en vivo" }).waitFor(LONG);
    return async (rec) => {
      await page.waitForTimeout(700);
      await humanHover(page, page.getByRole("img", { name: /QR|código/i }).first(), 1600);
      await humanHover(page, page.getByRole("status", { name: "Pagos indebidos" }), 1800);
      rec.mark("counter");
      await idle(page, TAIL + 2500);
    };
  },
};
