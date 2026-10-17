import { describe, expect, it } from "vitest";
import { createMockClient } from "@/lib/api/mock/mock-client";
import type { RedTeamEvent } from "@/lib/api/contracts";
import { applyEvent, INITIAL_ARENA } from "./arena-state";

async function scriptedEvents(rounds: number): Promise<RedTeamEvent[]> {
  const events: RedTeamEvent[] = [];
  await createMockClient({ latencyMs: 0 }).runRedTeam({ rounds }, (event) => events.push(event));
  return events;
}

describe("applyEvent", () => {
  it("builds one round per attack with its verdict and keeps the score", async () => {
    const state = (await scriptedEvents(2)).reduce(applyEvent, INITIAL_ARENA);

    expect(state.rounds).toHaveLength(2);
    expect(state.rounds[0].attack?.technique).toBe("Cuenta cambiada con logo idéntico");
    expect(state.rounds[0].decision?.status).toBe("hold");
    expect(state.score).toEqual({ attacks: 2, caught: 2, improper: 0 });
    expect(state.summary).toMatch(/0 pagos indebidos/);
  });

  it("counts an attack that got through as an improper payment", () => {
    const state = [
      { type: "round_started", round: 1 },
      { type: "verdict", round: 1, caught: false },
    ].reduce((s, e) => applyEvent(s, e as RedTeamEvent), INITIAL_ARENA);

    expect(state.score).toEqual({ attacks: 1, caught: 0, improper: 1 });
  });

  it("keeps the error message the stream sends", () => {
    const state = applyEvent(INITIAL_ARENA, { type: "error", round: 0, message: "Se agotó el tope diario." });

    expect(state.error).toBe("Se agotó el tope diario.");
  });
});
