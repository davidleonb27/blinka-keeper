import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { CustodioApi } from "@/lib/api/client";
import type { ChallengeAttempt } from "@/lib/api/contracts";
import { NetworkError } from "@/lib/api/errors";
import { decisionFrom, type FailingRules } from "@/lib/api/mock/decision-builder";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { Challenge } from "./challenge";
import { ChallengeStage } from "./challenge-stage";

function apiWith(overrides: Partial<CustodioApi>): CustodioApi {
  return { ...createMockClient({ latencyMs: 0 }), ...overrides };
}

function attemptWith(failing: FailingRules, broke_through = false): ChallengeAttempt {
  return {
    id: "A-0099",
    alias: null,
    technique: "Prueba",
    decision: decisionFrom({ invoice_id: "INV-77", supplier_name: null, amount: null, currency: null, failing, counterfactual: "" }),
    broke_through,
    at: "2026-10-17T15:00:00Z",
  };
}

async function attack(api: CustodioApi) {
  renderWithApi(<Challenge />, api);
  await userEvent.click(screen.getByRole("button", { name: /Intentar que pague/ }));
  return screen.findByRole("region", { name: "Resultado de tu intento" });
}

describe("Challenge", () => {
  it("says the wall is clean only when no attempt on it broke through", async () => {
    const mock = createMockClient({ latencyMs: 0 });
    const stats = await mock.getChallengeStats();
    const [first, ...rest] = stats.hall_of_fame;
    const api = apiWith({
      getChallengeStats: async () => ({
        ...stats,
        improper_payments: 1,
        hall_of_fame: [{ ...first, broke_through: true }, ...rest],
      }),
    });

    renderWithApi(<Challenge />, api);

    expect(await screen.findByText(/1 cobró un pago indebido/)).toBeInTheDocument();
    expect(screen.queryByText(/Ninguno cobró/)).not.toBeInTheDocument();
  });

  it("shows the error instead of a silent gap when the counter cannot be read", async () => {
    renderWithApi(<Challenge />, apiWith({ getChallengeStats: () => Promise.reject(new NetworkError()) }));

    expect(await screen.findByText(/No pudimos conectarnos con Custodio/)).toBeInTheDocument();
  });

  it("shows a held attempt as FRENADO with each rule that fired and why", async () => {
    const result = await attack(apiWith({ submitChallengeAttempt: async () => attemptWith({ account: "La cuenta no es la registrada." }) }));

    expect(within(result).getByRole("heading", { name: "FRENADO" })).toBeInTheDocument();
    const fired = within(result).getByRole("list", { name: "Reglas que se dispararon" });
    expect(within(fired).getByText(/R4 · Cuenta registrada/)).toBeInTheDocument();
    expect(within(fired).getByText("La cuenta no es la registrada.")).toBeInTheDocument();
  });

  it("shows an escalated attempt as ESCALADO", async () => {
    const result = await attack(apiWith({ submitChallengeAttempt: async () => attemptWith({ injection: "Trae órdenes para el agente." }) }));

    expect(within(result).getByRole("heading", { name: "ESCALADO" })).toBeInTheDocument();
    expect(within(result).getByText("Trae órdenes para el agente.")).toBeInTheDocument();
  });

  it("shows a clean invoice as PAGADO LEGÍTIMAMENTE with no rule fired", async () => {
    const result = await attack(apiWith({ submitChallengeAttempt: async () => attemptWith({}) }));

    expect(within(result).getByRole("heading", { name: "PAGADO LEGÍTIMAMENTE" })).toBeInTheDocument();
    expect(within(result).getByText(/Ninguna regla se disparó/)).toBeInTheDocument();
  });

  it("never dresses a payment the auditor vetoed as legitimate", async () => {
    const result = await attack(apiWith({ submitChallengeAttempt: async () => attemptWith({}, true) }));

    expect(within(result).getByRole("heading", { name: "PAGO INDEBIDO" })).toBeInTheDocument();
    expect(within(result).queryByText("PAGADO LEGÍTIMAMENTE")).not.toBeInTheDocument();
  });

  it("links every result to its acta in the panel", async () => {
    const result = await attack(apiWith({ submitChallengeAttempt: async () => attemptWith({ account: "Otra cuenta." }) }));

    expect(within(result).getByRole("link", { name: /Ver el acta/ })).toHaveAttribute("href", "/panel?acta=INV-77");
  });
});

describe("Challenge after a refused attempt", () => {
  it("drops the previous verdict so it is not read as the new one", async () => {
    let calls = 0;
    const result = await attack(
      apiWith({
        submitChallengeAttempt: async () => {
          calls += 1;
          if (calls > 1) throw new NetworkError();
          return attemptWith({ account: "Otra cuenta." });
        },
      }),
    );
    expect(result).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Intentar que pague/ }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Resultado de tu intento" })).not.toBeInTheDocument();
  });
});

describe("ChallengeStage", () => {
  it("shows a QR to this site's /reto", async () => {
    renderWithApi(<ChallengeStage />);

    const qr = await screen.findByRole("img", { name: /Código QR/ });
    expect(qr).toHaveAccessibleName(`Código QR a ${window.location.origin}/reto`);
    expect(screen.getByText(`${window.location.host}/reto`)).toBeInTheDocument();
  });

  it("puts the improper payments count front and center", async () => {
    renderWithApi(<ChallengeStage />);

    const counter = await screen.findByRole("status", { name: "Pagos indebidos" });
    expect(counter).toHaveTextContent("0");
  });

  it("shows the most recent attempt on the wall, not the most creative", async () => {
    const mock = createMockClient({ latencyMs: 0 });
    const stats = await mock.getChallengeStats();
    const [first, second] = stats.hall_of_fame;
    const api = apiWith({
      getChallengeStats: async () => ({
        ...stats,
        hall_of_fame: [
          { ...first, technique: "La más creativa", at: "2026-10-16T10:00:00Z" },
          { ...second, technique: "La más reciente", at: "2026-10-17T10:00:00Z" },
        ],
      }),
    });

    renderWithApi(<ChallengeStage />, api);

    const latest = await screen.findByRole("region", { name: "Último intento" });
    expect(within(latest).getByText("La más reciente")).toBeInTheDocument();
  });

  it("polls the counters every few seconds", async () => {
    let reads = 0;
    const mock = createMockClient({ latencyMs: 0 });
    renderWithApi(<ChallengeStage />, apiWith({ getChallengeStats: () => ((reads += 1), mock.getChallengeStats()) }));

    await waitFor(() => expect(reads).toBeGreaterThanOrEqual(2), { timeout: 4_500 });
  });
});
