import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CustodioApi } from "@/lib/api/client";
import { NetworkError } from "@/lib/api/errors";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { Challenge } from "./challenge";

function apiWith(overrides: Partial<CustodioApi>): CustodioApi {
  return { ...createMockClient({ latencyMs: 0 }), ...overrides };
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
});
