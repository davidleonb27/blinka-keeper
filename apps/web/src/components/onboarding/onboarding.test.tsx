import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderWithApi } from "@/test/render";
import { Onboarding } from "./onboarding";

async function pressEnter() {
  await userEvent.keyboard("{Enter}");
}

async function fillCompany(name = "Café La Montaña") {
  await userEvent.type(screen.getByLabelText("Nombre de la empresa"), name);
  await userEvent.type(screen.getByLabelText(/Sitio web/), "https://cafelamontana.co");
  await pressEnter();
  await screen.findByRole("heading", { name: `Esto entendimos de ${name}` });
}

describe("Onboarding", () => {
  it("asks one question per screen and shows progress", () => {
    renderWithApi(<Onboarding />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "¿Cómo se llama tu empresa?" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "1");
  });

  it("validates before advancing with Enter", async () => {
    renderWithApi(<Onboarding />);
    await userEvent.click(screen.getByLabelText("Nombre de la empresa"));

    await pressEnter();

    expect(screen.getByRole("alert")).toHaveTextContent("Escribe el nombre de tu empresa para seguir.");
    expect(screen.getByRole("heading", { name: "¿Cómo se llama tu empresa?" })).toBeInTheDocument();
  });

  it("advances with Enter and proposes a profile adapted to the company", async () => {
    renderWithApi(<Onboarding />);

    await fillCompany();

    expect(screen.getByLabelText("Industria")).toHaveValue("Alimentos y bebidas");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "2");
  });

  it("goes back without losing answers", async () => {
    renderWithApi(<Onboarding />);
    await fillCompany();

    await userEvent.click(screen.getByRole("button", { name: "Volver" }));

    expect(screen.getByLabelText("Nombre de la empresa")).toHaveValue("Café La Montaña");
  });

  it("runs the whole flow in mock mode until Custodio is ready", async () => {
    renderWithApi(<Onboarding />);
    await fillCompany();

    await pressEnter();
    await screen.findByRole("heading", { name: "País, moneda y saldo" });
    expect(screen.getByLabelText("Moneda base")).toHaveValue("COP");
    await pressEnter();

    await screen.findByRole("heading", { name: "¿Quién aprueba lo que se sale de las reglas?" });
    await pressEnter();
    expect(screen.getByRole("alert")).toHaveTextContent("Agrega al menos una persona que apruebe.");
    await userEvent.type(screen.getByLabelText("Nombre de quien aprueba"), "Ana Gómez");
    await userEvent.type(screen.getByLabelText(/Usuario de Telegram/), "@ana");
    await pressEnter();

    await screen.findByRole("heading", { name: "Tus reglas, en tus palabras" });
    await screen.findByText("Tope de aprobación automática");
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));

    await screen.findByRole("heading", { name: "¿A quién le pagas?" });
    await pressEnter();
    expect(screen.getByRole("alert")).toHaveTextContent("Sube una lista o usa la de ejemplo.");
    await userEvent.click(screen.getByRole("button", { name: "Usar una lista de ejemplo" }));
    await screen.findByText("Distribuidora Andina SAS");
    await pressEnter();

    await screen.findByRole("heading", { name: "Tu primera semana, decidida" });
    await waitFor(() => expect(screen.getByText(/facturas decididas/)).toBeInTheDocument());
    await pressEnter();

    await screen.findByRole("heading", { name: "Custodio está listo" });
    expect(screen.getByRole("link", { name: /Ir al panel/ })).toHaveAttribute("href", "/panel");
  });
});
