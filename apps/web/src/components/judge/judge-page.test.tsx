import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CRITERIA, PENDING_LANES, REAL_VS_SIMULATED, WALKTHROUGH } from "./judge-content";
import { JudgePage } from "./judge-page";

const RUBRIC = [
  ["Impacto en el reto", 30],
  ["Innovación", 20],
  ["Viabilidad técnica", 20],
  ["Viabilidad de implementación", 20],
  ["Presentación", 10],
] as const;

describe("judge content", () => {
  it("follows the rubric in order and its weights add up to 100", () => {
    expect(CRITERIA.map((c) => [c.title, c.weight])).toEqual(RUBRIC);
    expect(CRITERIA.reduce((sum, c) => sum + c.weight, 0)).toBe(100);
  });

  it("backs every claim with two to four claims per criterion and a proof per claim", () => {
    for (const criterion of CRITERIA) {
      expect(criterion.claims.length).toBeGreaterThanOrEqual(2);
      expect(criterion.claims.length).toBeLessThanOrEqual(4);
      for (const claim of criterion.claims) expect(claim.proofs.length).toBeGreaterThan(0);
    }
  });

  it("walks the jury through five steps", () => {
    expect(WALKTHROUGH).toHaveLength(5);
  });

  it("only flags lanes that are still on their way to main", () => {
    const flagged = new Set(CRITERIA.flatMap((c) => c.claims.flatMap((claim) => claim.proofs.map((p) => p.lane))));
    flagged.delete(undefined);
    expect([...flagged].every((lane) => lane && PENDING_LANES.includes(lane))).toBe(true);
  });

  it("says which parts are simulated", () => {
    const blinka = REAL_VS_SIMULATED.find((row) => row.part.startsWith("Blinka"));
    expect(blinka?.status).toBe("simulated");
    expect(REAL_VS_SIMULATED.find((row) => row.part.startsWith("Stripe"))?.status).toBe("real");
  });
});

describe("JudgePage", () => {
  it("shows one section per criterion with its weight", () => {
    render(<JudgePage />);

    for (const [title, weight] of RUBRIC) {
      const section = screen.getByRole("region", { name: new RegExp(`^${title}`) });
      expect(within(section).getByText(`${weight} %`)).toBeInTheDocument();
    }
  });

  it("links each proof to the product in one click", () => {
    render(<JudgePage />);

    const stripe = screen.getByRole("link", { name: /Ver un pago real en Stripe/ });
    expect(stripe).toHaveAttribute("href", "/panel?acta=F-004");
    expect(screen.getByRole("link", { name: /Engáñalo/ })).toHaveAttribute("href", "/reto");
    expect(screen.getByRole("link", { name: /Verifica un recibo alterado/ })).toHaveAttribute("href", "/verificar");
    expect(screen.getByRole("link", { name: /Conciliación y cierre/ })).toHaveAttribute("href", "/conciliacion");
    expect(screen.getByRole("link", { name: /Reglas en tus palabras/ })).toHaveAttribute("href", "/reglas");
    expect(screen.getByRole("link", { name: /WhatsApp real/ })).toHaveAttribute("href", "/panel");
    expect(screen.getByRole("link", { name: /Pedir corrección/ })).toHaveAttribute("href", "/panel?acta=F-039");
  });

  it("numbers the two-minute walkthrough", () => {
    render(<JudgePage />);

    const walk = screen.getByRole("region", { name: /Recorrido de 2 minutos/ });
    expect(within(walk).getAllByRole("listitem")).toHaveLength(5);
  });

  it("has an honest real-versus-simulated table and the adoption section", () => {
    render(<JudgePage />);

    const table = screen.getByRole("table", { name: /Real vs\. simulado/ });
    expect(within(table).getAllByRole("row")).toHaveLength(REAL_VS_SIMULATED.length + 1);
    expect(within(table).getByText(/pain\.001/)).toBeInTheDocument();
    const adoption = screen.getByRole("region", { name: "Cómo lo adopta una empresa" });
    expect(within(adoption).getByText(/Lo que falta para producción/)).toBeInTheDocument();
    expect(within(adoption).getAllByText(/NO MEDIDO/).length).toBeGreaterThan(0);
  });
});
