import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "*.prod.ts",
  workers: 1,
  retries: 0,
  timeout: 420_000,
  expect: { timeout: 30_000 },
  reporter: [["list"]],
  use: {
    baseURL: "https://blinka-keeper.vercel.app",
    trace: "retain-on-failure",
    launchOptions: { executablePath: "/opt/pw-browsers/chromium" },
  },
  projects: [{ name: "bogota", use: { ...devices["Desktop Chrome"], locale: "es-CO", timezoneId: "America/Bogota" } }],
});
