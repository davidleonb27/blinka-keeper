import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { watch } from "./problems";

/**
 * Cold loads as a visitor in Bogotá gets them from the CDN: the shell (layout, navigation) hydrates first and asks the
 * API for the workspace while the page's own code is still on its way. When that code arrives, its components hydrate
 * against server HTML that never had data. Each page's code is recognised by a sentence only that page renders.
 */

const PAGE_CODE_LATE_MS = 1_500;
const PAGES: { path: string; heading: string | RegExp; sentence: string }[] = [
  { path: "/", heading: "Tu analista de cuentas por pagar", sentence: "El modelo lee, el código decide" },
  { path: "/reto", heading: "Róbale a Blinka Keeper", sentence: "Intenta que pague algo indebido" },
  { path: "/panel", heading: "Panel", sentence: "Lo que Blinka Keeper decidió este mes" },
  { path: "/reglas", heading: "Reglas", sentence: "Tú pones los límites" },
  { path: "/arena", heading: /Arena/, sentence: "Un atacante genera facturas" },
  { path: "/registro", heading: "Registro", sentence: "Cada decisión queda encadenada" },
];
const PANEL_CODE = ["Lo que Blinka Keeper decidió este mes", "Acta de decisión"];
const WORKSPACE_COOKIE = "custodio_ws";

interface DemoWorkspace {
  id: string;
  decisionId: string;
}

/** A demo workspace whose invoices are already decided, made through the API as a returning visitor has it. */
async function decidedDemo(request: APIRequestContext): Promise<DemoWorkspace> {
  const created = await (await request.post("/api/v1/workspaces", { data: { mode: "demo" } })).json();
  const headers = { "X-Custodio-Workspace": created.workspace_id };
  expect((await request.post("/api/v1/invoices/process", { headers })).ok()).toBe(true);
  const [first] = await (await request.get("/api/v1/decisions", { headers })).json();
  return { id: created.workspace_id, decisionId: first.decision.invoice_id };
}

/** Each test's browser context is new (empty caches); with the cookie it is a returning visitor's cold load. */
async function returningVisitor(page: Page, baseURL: string | undefined, workspace: DemoWorkspace) {
  await page.context().addCookies([{ name: WORKSPACE_COOKIE, value: workspace.id, url: baseURL ?? "" }]);
}

async function pageCodeArrivesLate(page: Page, sentences: string[]) {
  await page.route("**/_next/static/chunks/**", async (route) => {
    const response = await route.fetch();
    const body = await response.text();
    if (sentences.some((sentence) => body.includes(sentence))) {
      await new Promise((resolve) => setTimeout(resolve, PAGE_CODE_LATE_MS));
    }
    await route.fulfill({ response, body });
  });
}

function apiCalls(page: Page): string[] {
  const calls: string[] = [];
  page.on("request", (request) => {
    const { pathname } = new URL(request.url());
    if (pathname.startsWith("/api/v1/")) calls.push(`${request.method()} ${pathname.slice("/api/v1".length)}`);
  });
  return calls;
}

test.describe("cold loads in Bogotá with the server in UTC", () => {
  let workspace: DemoWorkspace;

  test.beforeAll(async ({ request }) => {
    workspace = await decidedDemo(request);
  });

  for (const { path, heading, sentence } of PAGES) {
    test(`${path} hydrates without a mismatch when its own code arrives after the shell's data`, async ({ page, baseURL }) => {
      await returningVisitor(page, baseURL, workspace);
      const problems = watch(page);
      await pageCodeArrivesLate(page, [sentence]);

      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
      await page.waitForLoadState("networkidle");

      expect(problems.list, problems.list.join("\n")).toEqual([]);
    });
  }

  test("a cookie naming a workspace the API no longer has is replaced by a new demo", async ({ page, baseURL }) => {
    const stale = "ws_borrado_al_reiniciar_la_base";
    await page.context().addCookies([{ name: WORKSPACE_COOKIE, value: stale, url: baseURL ?? "" }]);
    const calls = apiCalls(page);

    await page.goto("/panel");

    await expect(page.getByRole("region", { name: "Facturas por decidir" })).toBeVisible();
    await expect(page.getByText("No encontramos eso en tu espacio de trabajo.")).toHaveCount(0);
    const cookie = (await page.context().cookies()).find(({ name }) => name === WORKSPACE_COOKIE);
    expect(cookie?.value).toBeTruthy();
    expect(cookie?.value).not.toBe(stale);
    expect(calls.filter((call) => call === "POST /workspaces")).toHaveLength(1);
  });

  test("the panel's HTML already carries the panel, so a deep link never starts from an empty main", async ({
    request,
  }) => {
    const html = await (await request.get(`/panel?acta=${workspace.decisionId}`)).text();
    const main = html.slice(html.indexOf("<main"), html.indexOf("</main>"));

    expect(main).toContain(PANEL_CODE[0]);
  });

  for (const deepLink of ["/panel?acta={id}", "/acta/{id}"]) {
    for (const late of [false, true]) {
      test(`a fresh load of ${deepLink} opens the panel with the acta on top${late ? ", code arriving late" : ""}`, async ({
        page,
        baseURL,
      }) => {
        const id = workspace.decisionId;
        await returningVisitor(page, baseURL, workspace);
        const problems = watch(page);
        const calls = apiCalls(page);
        if (late) await pageCodeArrivesLate(page, PANEL_CODE);

        await page.goto(deepLink.replace("{id}", id));

        await expect(page).toHaveURL(new RegExp(`/panel\\?acta=${id}$`));
        const acta = page.getByRole("dialog");
        await expect(acta.getByText(`Acta de decisión · ${id}`)).toBeVisible();
        await expect(acta.getByRole("list", { name: "Reglas evaluadas" }).getByRole("listitem")).toHaveCount(15);
        // Under the modal acta the panel is aria-hidden, so it is looked up including hidden elements.
        await expect(page.getByRole("heading", { level: 1, name: "Panel", includeHidden: true })).toBeAttached();
        await expect(page.getByRole("region", { name: "Facturas", includeHidden: true })).toBeAttached();
        await page.waitForLoadState("networkidle");
        expect(calls).toEqual(expect.arrayContaining(["GET /decisions", `GET /decisions/${id}`]));
        expect(problems.list, problems.list.join("\n")).toEqual([]);
      });
    }
  }
});
