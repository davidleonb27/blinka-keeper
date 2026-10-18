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

  it("shows what already works in production, each card linking to try it", () => {
    renderWithApi(<HomePage />);
    const section = screen.getByRole("region", { name: /Del WhatsApp al cierre de mes/ });
    const cards = within(section).getAllByRole("listitem");
    expect(cards).toHaveLength(6);
    expect(within(section).getByRole("link", { name: /Ver el cuadre con Stripe/ })).toHaveAttribute("href", "/pagos");
    expect(within(section).getByRole("link", { name: /Probar un recibo alterado/ })).toHaveAttribute("href", "/verificar");
  });

  it("closes on a dark band with two questions that open the demo", () => {
    renderWithApi(<HomePage />);
    const closing = screen.getByRole("region", { name: /Cuántas facturas pagas al mes/ });
    expect(within(closing).getByRole("group", { name: "Facturas al mes" })).toBeInTheDocument();
    expect(within(closing).getByRole("button", { name: /Ver cómo lo haría Blinka Keeper/ })).toBeInTheDocument();
    expect(within(closing).getByRole("link", { name: /Róbale a Blinka Keeper/ })).toHaveAttribute("href", "/reto");
  });

  it("names only the rails it really uses, as text, with no borrowed logos", () => {
    renderWithApi(<HomePage />);
    const hero = screen.getByRole("region", { name: "Tu analista de cuentas por pagar" });
    expect(within(hero).getAllByText("Stripe · modo prueba")[0]).toBeInTheDocument();
    expect(within(hero).getAllByText("ISO 20022 pain.001")[0]).toBeInTheDocument();
    expect(within(hero).queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByText(/Visa|Mastercard|Mercado Pago|Marcas que confían/)).not.toBeInTheDocument();
  });

  it("answers the questions a finance team asks, including what it does not do", () => {
    renderWithApi(<HomePage />);
    const faq = screen.getByRole("region", { name: "Lo que pregunta un equipo de finanzas" });
    expect(within(faq).getAllByRole("listitem")).toHaveLength(6);
    expect(faq).toHaveTextContent("modo prueba");
    expect(faq).toHaveTextContent("No consulta a la DIAN ni al SAT");
  });
});
