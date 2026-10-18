/** Where the project lives and the figures the public site may state. Only measured figures go here. */

export const REPO_SLUG = "davidleonb27/blinka-keeper";
export const REPO_URL = `https://github.com/${REPO_SLUG}`;
export const DEMO_URL = "https://custodio-blinka-green.vercel.app";
export const LICENSE_NAME = "MIT";

export function repoFile(path: string): string {
  return `${REPO_URL}/blob/main/${path}`;
}

const NEON_STORE = [{ type: "integration", integrationSlug: "neon", productSlug: "neon", protocol: "storage" }];

/** Vercel's clone flow: this repository plus a Neon database from the Vercel Marketplace (it injects DATABASE_URL). */
export const VERCEL_DEPLOY_URL = `https://vercel.com/new/clone?${new URLSearchParams({
  "repository-url": REPO_URL,
  "project-name": "custodio",
  "repository-name": "custodio",
  stores: JSON.stringify(NEON_STORE),
})}`;

export interface MeasuredFigure {
  value: string;
  label: string;
  detail: string;
}

/** Measured on 2026-10-17; the commands and raw outputs are in docs/DATASET.md and docs/MEASUREMENTS.md. */
export const MEASURED_FIGURES: readonly MeasuredFigure[] = [
  {
    value: "0",
    label: "pagos indebidos en la prueba de estrés",
    detail: "1.000 empresas simuladas y 25.139 facturas; el auditor re-revisó 8.136 pagos.",
  },
  {
    value: "36/36",
    label: "decisiones correctas en el dataset dorado",
    detail: "36 facturas etiquetadas, con trampas: duplicados, cuentas cambiadas, fraccionamientos y más.",
  },
  {
    value: "15",
    label: "reglas en código, sin modelo",
    detail: "El modelo sólo lee y cita. Mismo input, misma decisión, siempre.",
  },
];
export const MEASUREMENTS_URL = repoFile("docs/DATASET.md");
