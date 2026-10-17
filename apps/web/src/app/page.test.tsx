import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GitHubStars } from "@/components/site/github-stars";
import { RAIL_PITCH } from "@/lib/presentation";
import { REPO_URL } from "@/lib/site";
import { renderWithApi } from "@/test/render";
import HomePage from "./page";

// The live count is an async server component; here it stands still so the page renders in jsdom.
vi.mock("@/components/site/live-github-stars", () => ({ LiveGitHubStars: () => <GitHubStars count={42} /> }));

describe("HomePage", () => {
  it("says Custodio decides and the rail pays", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByText(RAIL_PITCH)).toBeInTheDocument();
  });

  it("presents the open-source agent with the demo and the one-command self-hosting", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "El agente de cuentas por pagar de código abierto" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Probar la demo/ })[0]).toHaveAttribute("href", "/panel");
    expect(screen.getByRole("link", { name: /Autoalojar en 1 comando/ })).toHaveAttribute("href", "/docs/inicio-rapido#autoalojado");
  });

  it("shows the compose command and a call to the firewall", () => {
    renderWithApi(<HomePage />);

    const code = screen.getByRole("figure", { name: /Autoalojado/ });
    expect(code).toHaveTextContent("docker compose up --build");
    expect(code).toHaveTextContent("/api/v1/firewall/intents");
  });

  it("lists the six features with their docs", () => {
    renderWithApi(<HomePage />);

    const features = within(screen.getByRole("region", { name: /Todo lo que necesita/ })).getAllByRole("listitem");
    expect(features.map((item) => item.querySelector("h3")?.textContent)).toEqual([
      "Lectura con evidencia",
      "12 reglas en código",
      "Auditor independiente",
      "Registro encadenado SHA-256",
      "Firewall de pagos por API y MCP",
      "Rieles de pago enchufables",
    ]);
  });

  it("publishes only measured figures, with their source", () => {
    renderWithApi(<HomePage />);

    const metrics = screen.getByRole("region", { name: /Medido, no prometido/ });
    expect(metrics).toHaveTextContent("1.000 empresas simuladas");
    expect(metrics).toHaveTextContent("25.139 facturas");
    expect(metrics).toHaveTextContent("36/36");
    expect(within(metrics).getByRole("link", { name: /Cómo se midió/ })).toHaveAttribute("href", expect.stringContaining(REPO_URL));
  });

  it("links the repository with the live star count and the self-hosting options", () => {
    renderWithApi(<HomePage />);

    const openSource = screen.getByRole("region", { name: /Código abierto/ });
    expect(within(openSource).getByText("42")).toBeInTheDocument();
    expect(within(openSource).getAllByRole("link", { name: /GitHub/ })[0]).toHaveAttribute("href", REPO_URL);
    const selfHost = screen.getByRole("region", { name: /Autoalójalo/ });
    expect(selfHost).toHaveTextContent("Vercel");
    expect(selfHost).toHaveTextContent("docker compose");
  });
});
