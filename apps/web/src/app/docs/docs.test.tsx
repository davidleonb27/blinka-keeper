import { render, screen, within } from "@testing-library/react";
import type { ComponentType } from "react";
import { describe, expect, it, vi } from "vitest";
import { DocsSidebar } from "@/components/site/docs-sidebar";
import { RULES } from "@/lib/api/contracts";
import { DOCS_PAGES } from "@/lib/docs";
import ApiPage from "./api/page";
import ConfigurationPage from "./configuracion/page";
import ContributePage from "./contribuir/page";
import FirewallPage from "./firewall/page";
import QuickstartPage from "./inicio-rapido/page";
import McpPage from "./mcp/page";
import IntroductionPage from "./page";
import RulesPage from "./reglas/page";
import RailsPage from "./rieles/page";
import SecurityPage from "./seguridad/page";

vi.mock("next/navigation", () => ({ usePathname: () => "/docs/reglas" }));

const PAGES: Record<string, ComponentType> = {
  "/docs": IntroductionPage,
  "/docs/inicio-rapido": QuickstartPage,
  "/docs/configuracion": ConfigurationPage,
  "/docs/reglas": RulesPage,
  "/docs/seguridad": SecurityPage,
  "/docs/firewall": FirewallPage,
  "/docs/mcp": McpPage,
  "/docs/rieles": RailsPage,
  "/docs/api": ApiPage,
  "/docs/contribuir": ContributePage,
};

describe("docs pages", () => {
  it.each(DOCS_PAGES)("$href is titled «$title»", ({ href, title }) => {
    const Page = PAGES[href];
    render(<Page />);

    expect(screen.getByRole("heading", { level: 1, name: title })).toBeInTheDocument();
  });

  it("explains the twelve rules with their effect", () => {
    render(<RulesPage />);

    const rows = within(screen.getByRole("table", { name: /Las 15 reglas/ })).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.querySelector("th")?.textContent)).toEqual(RULES.map((rule) => rule.id));
  });

  it("documents every environment variable", () => {
    render(<ConfigurationPage />);

    for (const name of [
      "ANTHROPIC_API_KEY",
      "DATABASE_URL",
      "CUSTODIO_PAYMENT_RAIL",
      "STRIPE_SECRET_KEY",
      "CUSTODIO_LLM_DAILY_BUDGET_USD",
      "CUSTODIO_PUBLIC_BASE_URL",
      "API_INTERNAL_URL",
    ]) {
      expect(screen.getByRole("rowheader", { name: name })).toBeInTheDocument();
    }
  });

  it("sends the API reference to the interactive docs of the API itself", () => {
    render(<ApiPage />);

    expect(screen.getByRole("link", { name: /Abrir la referencia interactiva/ })).toHaveAttribute("href", "/api/v1/docs");
  });

  it("gives the self-hosting steps an anchor the landing links to", () => {
    render(<QuickstartPage />);

    expect(document.getElementById("autoalojado")).toHaveTextContent("Autoalojado");
  });
});

describe("DocsSidebar", () => {
  it("lists every page and marks the current one", () => {
    render(<DocsSidebar />);

    const nav = screen.getByRole("navigation", { name: "Documentación" });
    expect(within(nav).getAllByRole("link")).toHaveLength(DOCS_PAGES.length);
    expect(within(nav).getByRole("link", { name: "Reglas R1–R15" })).toHaveAttribute("aria-current", "page");
  });
});
