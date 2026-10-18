import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RAIL_PITCH } from "@/lib/presentation";
import { REPO_URL } from "@/lib/site";
import { renderWithApi } from "@/test/render";
import HomePage from "./page";

// The live count is an async server component; here it stands still so the page renders in jsdom.

describe("HomePage", () => {
  it("says Blinka Keeper decides and the rail pays", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByText(RAIL_PITCH)).toBeInTheDocument();
  });

  it("opens on what Blinka Keeper does for a finance team, with the demo first and the challenge as a quiet link", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "Tu analista de cuentas por pagar" })).toBeInTheDocument();
    expect(screen.getByText(/Lee, decide, paga, concilia y cierra el mes;/)).toHaveTextContent("tú solo apruebas lo que importa");
    const hero = screen.getByRole("region", { name: "Tu analista de cuentas por pagar" });
    expect(within(hero).getByRole("link", { name: /Probar la demo/ })).toHaveAttribute("href", "/panel");
    expect(within(hero).getByRole("link", { name: /Intenta engañarlo/ })).toHaveAttribute("href", "/reto");
    expect(within(hero).queryByRole("link", { name: /Róbale a Blinka Keeper/ })).not.toBeInTheDocument();
    expect(within(hero).queryByRole("figure")).not.toBeInTheDocument();
  });

  it("shows the compose command and a call to the firewall in the self-hosting section", () => {
    renderWithApi(<HomePage />);

    const code = within(screen.getByRole("region", { name: /Autoalójalo/ })).getByRole("figure", { name: /Autoalojado/ });
    expect(code).toHaveTextContent("docker compose up --build");
    expect(code).toHaveTextContent("/api/v1/firewall/intents");
  });

  it("lists the six features with their docs", () => {
    renderWithApi(<HomePage />);

    const features = within(screen.getByRole("region", { name: /Todo lo que necesita/ })).getAllByRole("listitem");
    expect(features.map((item) => item.querySelector("h3")?.textContent)).toEqual([
      "Lectura con evidencia",
      "15 reglas en código",
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

  it("links the repository without a star count, and the self-hosting options", () => {
    renderWithApi(<HomePage />);

    const openSource = screen.getByRole("region", { name: /Código abierto/ });
    expect(within(openSource).queryByText(/★|estrellas/i)).not.toBeInTheDocument();
    expect(within(openSource).getAllByRole("link", { name: /GitHub/ })[0]).toHaveAttribute("href", REPO_URL);
    const selfHost = screen.getByRole("region", { name: /Autoalójalo/ });
    expect(selfHost).toHaveTextContent("Vercel");
    expect(selfHost).toHaveTextContent("docker compose");
  });
});
