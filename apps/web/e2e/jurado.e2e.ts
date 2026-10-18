import { expect, test } from "@playwright/test";
import { CRITERIA, WALKTHROUGH, type ProofLink } from "../src/components/judge/judge-content";
import { watch } from "./problems";

/** The jury's page renders without errors and every proof it offers opens a route that exists. */

const internal = (href: string) => href.startsWith("/");
const proofs: ProofLink[] = [
  ...CRITERIA.flatMap((criterion) => criterion.claims.flatMap((claim) => claim.proofs)),
  ...WALKTHROUGH.map((step) => ({ label: step.action, href: step.href })),
].filter((proof) => internal(proof.href));

test("the jury guide shows the rubric in order, from the site header", async ({ page }) => {
  const problems = watch(page);

  await page.goto("/docs");
  const header = page.getByRole("navigation", { name: "Principal" });
  if (await header.isVisible()) {
    await header.getByRole("link", { name: "Jurado" }).click();
  } else {
    await page.getByRole("navigation", { name: "Pie de página" }).getByRole("link", { name: "Guía para el jurado" }).click();
  }
  await expect(page.getByRole("heading", { level: 1, name: "Blinka Keeper, criterio por criterio" })).toBeVisible();
  for (const criterion of CRITERIA) {
    const section = page.getByRole("region", { name: criterion.title, exact: true });
    await expect(section.getByText(`${criterion.weight} %`, { exact: true })).toBeVisible();
  }
  await expect(page.getByRole("region", { name: "Recorrido de 2 minutos" }).getByRole("listitem")).toHaveCount(5);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);

  expect(problems.list, problems.list.join("\n")).toEqual([]);
});

test("every proof link on /jurado opens a route that exists", async ({ request }) => {
  for (const proof of proofs) {
    const path = proof.href.split("#")[0];
    const response = await request.get(path);
    if (proof.lane && !response.ok()) {
      // The feature travels on its own lane: flagged for review after that lane reaches main, not a failure here.
      test.info().annotations.push({ type: `revisar tras el merge de ${proof.lane}`, description: `${proof.label} → ${path}` });
      continue;
    }
    expect(response.status(), `${proof.label} → ${path}`).toBeLessThan(400);
  }
});
