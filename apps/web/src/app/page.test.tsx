import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RAIL_PITCH } from "@/lib/presentation";
import { REPO_URL } from "@/lib/site";
import { renderWithApi } from "@/test/render";
import HomePage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

// The live count is an async server component; here it stands still so the page renders in jsdom.

describe("HomePage", () => {
  it("says Custodio decides and the rail pays", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByText(RAIL_PITCH)).toBeInTheDocument();
  });

  it("opens on what Custodio does for a finance team, with the demo first and the challenge as a quiet link", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: "Tu analista de cuentas por pagar." })).toBeInTheDocument();
    const hero = screen.getByRole("region", { name: "Tu analista de cuentas por pagar." });
    expect(hero).toHaveTextContent("Cuentas por pagar, sin sustos");
    expect(hero).toHaveTextContent("Lee, decide, paga, concilia y cierra el mes. Tú solo apruebas lo que importa.");
    expect(hero).toHaveTextContent("Hecho para el reto Blinka · Hackathon 30X");
    expect(within(hero).getByRole("link", { name: /Probar la demo/ })).toHaveAttribute("href", "/panel");
    expect(within(hero).getByRole("link", { name: "Usar con mi empresa" })).toHaveAttribute("href", "/empezar");
    expect(within(hero).getByRole("link", { name: /Intenta engañarlo/ })).toHaveAttribute("href", "/reto");
    expect(within(hero).queryByRole("link", { name: /Róbale a Custodio/ })).not.toBeInTheDocument();
    expect(within(hero).queryByRole("figure")).not.toBeInTheDocument();
  });

  it("shows the compose command and a call to the firewall in the self-hosting section", () => {
    renderWithApi(<HomePage />);

    const code = within(screen.getByRole("region", { name: /Autoalójalo/ })).getByRole("figure", { name: /Autoalojado/ });
    expect(code).toHaveTextContent("docker compose up --build");
    expect(code).toHaveTextContent("/api/v1/firewall/intents");
  });

  it("shows the acta, the panel and the reconciliation as the product", () => {
    renderWithApi(<HomePage />);

    const product = screen.getByRole("region", { name: /Cada pago, explicado/ });
    for (const name of ["Ejemplo de acta", "Ejemplo del panel", "Ejemplo de conciliación"]) {
      expect(within(product).getByRole("figure", { name })).toBeInTheDocument();
    }
  });

  it("closes with two questions that lead to the demo", async () => {
    renderWithApi(<HomePage />);

    const closing = screen.getByRole("region", { name: "¿Cuántas facturas pagas al mes?" });
    expect(within(closing).getAllByRole("group")).toHaveLength(2);
    await userEvent.click(within(closing).getByRole("radio", { name: "Más de 500" }));
    await userEvent.click(within(closing).getByRole("button", { name: /Ver cómo lo haría Custodio/ }));
    expect(push).toHaveBeenCalledWith("/panel");
    expect(within(closing).getByRole("link", { name: /Róbale a Custodio/ })).toHaveAttribute("href", "/reto");
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
