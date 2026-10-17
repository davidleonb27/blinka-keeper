import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { RailBadge } from "./rail-badge";

describe("RailBadge", () => {
  it("names the simulated rail when nothing real pays", async () => {
    renderWithApi(<RailBadge />);

    expect(await screen.findByText("Riel: Simulado")).toBeInTheDocument();
  });

  it("names Stripe in test mode when the API pays through it", async () => {
    const api = {
      ...createMockClient({ latencyMs: 0 }),
      health: async () => ({ status: "ok", version: "test", anthropic: true, payment_rail: "stripe_test" as const }),
    };
    renderWithApi(<RailBadge />, api);

    expect(await screen.findByText("Riel: Stripe · modo prueba")).toBeInTheDocument();
  });
});
