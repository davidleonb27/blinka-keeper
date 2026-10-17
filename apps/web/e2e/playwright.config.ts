import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import path from "node:path";

// The walk runs against the real API (tests/e2e_app.py: production wiring with the model lanes swapped for
// deterministic doubles) on a fresh SQLite file, and a production build of the web that forwards /api/v1 to it.
const WEB_ROOT = path.resolve(__dirname, "..");
const API_PORT = 8765;
const WEB_PORT = 3100;
const API_URL = `http://127.0.0.1:${API_PORT}`;
const DATABASE = path.join(tmpdir(), `custodio-e2e-${process.pid}.db`);
const WEB_URL = `http://127.0.0.1:${WEB_PORT}`;

export default defineConfig({
  testDir: ".",
  testMatch: "*.e2e.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: { baseURL: WEB_URL, trace: "retain-on-failure" },
  projects: [
    {
      name: "bogota",
      use: { ...devices["Desktop Chrome"], locale: "es-CO", timezoneId: "America/Bogota" },
    },
    {
      // Far from the company's time zone and the server's, in another locale, dark, without motion and with a
      // theme and an API key already in localStorage: any render that depends on the browser's clock, locale,
      // theme, motion settings or storage shows up as a hydration error.
      name: "tokio-oscuro",
      use: {
        ...devices["Pixel 7"],
        locale: "en-US",
        timezoneId: "Asia/Tokyo",
        colorScheme: "dark",
        contextOptions: { reducedMotion: "reduce" },
        storageState: {
          cookies: [],
          origins: [
            {
              origin: WEB_URL,
              localStorage: [
                { name: "theme", value: "dark" },
                { name: "custodio_api_key", value: "cus_guardada_en_otra_visita" },
              ],
            },
          ],
        },
      },
    },
  ],
  webServer: [
    {
      command: `rm -f ${DATABASE} && uv run --frozen --directory ../api uvicorn tests.e2e_app:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: WEB_ROOT,
      url: `${API_URL}/api/v1/health`,
      env: { CUSTODIO_DATABASE_URL: `sqlite:///${DATABASE}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx next build && npx next start --hostname 127.0.0.1 --port ${WEB_PORT}`,
      cwd: WEB_ROOT,
      url: WEB_URL,
      env: { API_INTERNAL_URL: API_URL },
      reuseExistingServer: false,
      timeout: 600_000,
    },
  ],
});
