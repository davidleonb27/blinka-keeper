import type { Page } from "@playwright/test";

/** What the e2e never accepts: console errors, uncaught exceptions (React's #418 included) and failed requests. */
export interface Problems {
  list: string[];
}

export function watch(page: Page): Problems {
  const problems: Problems = { list: [] };
  page.on("console", (message) => {
    if (message.type() === "error") problems.list.push(`console en ${page.url()}: ${message.text()}`);
  });
  page.on("pageerror", (error) => problems.list.push(`excepción en ${page.url()}: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() >= 400) {
      problems.list.push(`HTTP ${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  page.on("requestfailed", (request) => {
    // Navigating away aborts in-flight prefetches; that is the browser, not a failure of the app.
    if (request.failure()?.errorText !== "net::ERR_ABORTED") {
      problems.list.push(`falló ${request.method()} ${request.url()}: ${request.failure()?.errorText}`);
    }
  });
  return problems;
}
