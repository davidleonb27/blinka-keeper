import { describe, expect, it } from "vitest";
import { DOCS_PAGES, neighbours } from "./docs";

describe("DOCS_PAGES", () => {
  it("covers the documentation the project promises, in reading order", () => {
    expect(DOCS_PAGES.map((page) => page.title)).toEqual([
      "Introducción",
      "Inicio rápido",
      "Configuración",
      "Reglas R1–R15",
      "Modelo de seguridad",
      "Firewall por API",
      "MCP",
      "Rieles de pago",
      "Referencia de la API",
      "Contribuir",
    ]);
  });

  it("gives every page its own address under /docs", () => {
    const hrefs = DOCS_PAGES.map((page) => page.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
    expect(hrefs.every((href) => href === "/docs" || href.startsWith("/docs/"))).toBe(true);
  });
});

describe("neighbours", () => {
  it("links each page to the one before and after it", () => {
    expect(neighbours("/docs")).toEqual({ previous: null, next: DOCS_PAGES[1] });
    expect(neighbours("/docs/contribuir")).toEqual({ previous: DOCS_PAGES[8], next: null });
  });
});
