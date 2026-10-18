import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import path from "node:path";

// Like playwright.config.ts, but the API pays through the real Stripe rail over the fake Stripe transport of the
// payment tests (tests/e2e_app.py with CUSTODIO_E2E_STRIPE=fake): the acta's «Pago en Stripe» and /pagos, no key.
// Its own ports, so it never reuses the servers of the main walk. Run: `npm run e2e:stripe`.
const WEB_ROOT = path.resolve(__dirname, "..");
const API_PORT = 8766;
const WEB_PORT = 3101;
const API_URL = `http://127.0.0.1:${API_PORT}`;
const DATABASE = path.join(tmpdir(), `custodio-e2e-stripe-${process.pid}.db`);
const WEB_URL = `http://127.0.0.1:${WEB_PORT}`;
const SERVER_TIME_ZONE = "UTC";
const PHONE_WIDTH = 390;

export default defineConfig({
  testDir: ".",
  testMatch: "*.stripe-e2e.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: { baseURL: WEB_URL, trace: "retain-on-failure" },
  projects: [
    { name: "bogota", use: { ...devices["Desktop Chrome"], locale: "es-CO", timezoneId: "America/Bogota" } },
    {
      name: "celular-390",
      use: {
        ...devices["Pixel 7"],
        viewport: { width: PHONE_WIDTH, height: 844 },
        locale: "es-CO",
        timezoneId: "America/Bogota",
        contextOptions: { reducedMotion: "reduce" },
      },
    },
  ],
  webServer: [
    {
      command: `rm -f ${DATABASE} && uv run --frozen --directory ../api uvicorn tests.e2e_app:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: WEB_ROOT,
      url: `${API_URL}/api/v1/health`,
      env: { CUSTODIO_DATABASE_URL: `sqlite:///${DATABASE}`, CUSTODIO_E2E_STRIPE: "fake", TZ: SERVER_TIME_ZONE },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx next build && npx next start --hostname 127.0.0.1 --port ${WEB_PORT}`,
      cwd: WEB_ROOT,
      url: WEB_URL,
      env: { API_INTERNAL_URL: API_URL, TZ: SERVER_TIME_ZONE },
      reuseExistingServer: false,
      timeout: 600_000,
    },
  ],
});
