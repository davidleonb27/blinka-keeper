import { describe, expect, it } from "vitest";
import { isStaleDeployError } from "./stale-deploy";

describe("isStaleDeployError", () => {
  it("recognises the errors of a tab opened before a deploy", () => {
    const chunk = new Error("Loading chunk 123 failed.");
    chunk.name = "ChunkLoadError";
    expect(isStaleDeployError(chunk)).toBe(true);
    expect(isStaleDeployError(new TypeError("Failed to fetch dynamically imported module: /_next/x.js"))).toBe(true);
    expect(isStaleDeployError(new TypeError("Importing a module script failed."))).toBe(true);
  });

  it("leaves every other error to the error screen", () => {
    expect(isStaleDeployError(new Error("Cannot read properties of undefined"))).toBe(false);
    expect(isStaleDeployError("network down")).toBe(false);
  });
});
