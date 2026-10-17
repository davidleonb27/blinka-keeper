// Generates src/lib/api/schema.gen.ts from the FastAPI app (apps/api main:app), the source of truth for every
// shape the web reads or sends. `npm run gen:api` writes it; `npm run check:api` (run by ./scripts/check.sh) fails
// when the committed file is stale, so a contract drift breaks the gate instead of production.
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const WEB_ROOT = fileURLToPath(new URL("..", import.meta.url));
const TARGET = fileURLToPath(new URL("../src/lib/api/schema.gen.ts", import.meta.url));
const EXPORT_OPENAPI = "import json, sys; from main import app; json.dump(app.openapi(), sys.stdout)";
const MAX_SCHEMA_BYTES = 32 * 1024 * 1024;
const HEADER = `/**
 * Generated from the FastAPI OpenAPI document (apps/api main:app, /api/v1/openapi.json) by
 * scripts/gen-api-schema.mjs. Do not edit: run \`npm run gen:api\`. ./scripts/check.sh fails when it is stale.
 */

`;

function exportOpenApi() {
  const json = execFileSync("uv", ["run", "--frozen", "--quiet", "--directory", "../api", "python", "-c", EXPORT_OPENAPI], {
    cwd: WEB_ROOT,
    encoding: "utf8",
    maxBuffer: MAX_SCHEMA_BYTES,
    stdio: ["ignore", "pipe", "inherit"],
  });
  return JSON.parse(json);
}

async function generate() {
  return HEADER + astToString(await openapiTS(exportOpenApi()));
}

function readCommitted() {
  try {
    return readFileSync(TARGET, "utf8");
  } catch {
    return null;
  }
}

const generated = await generate();
if (process.argv.includes("--check")) {
  if (readCommitted() !== generated) {
    console.error("src/lib/api/schema.gen.ts no coincide con la API. Corre `npm run gen:api` y revisa los tipos.");
    process.exit(1);
  }
  console.log("schema.gen.ts coincide con la API.");
} else {
  writeFileSync(TARGET, generated);
  console.log("schema.gen.ts regenerado desde la API.");
}
