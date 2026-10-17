import type { AttackSpec, Decision, RedTeamEvent } from "@/lib/api/contracts";

export interface ArenaRound {
  round: number;
  attack: AttackSpec | null;
  decision: Decision | null;
  caught: boolean | null;
}

export interface ArenaState {
  rounds: ArenaRound[];
  score: { attacks: number; caught: number; improper: number };
  summary: string | null;
  error: string | null;
}

export const INITIAL_ARENA: ArenaState = {
  rounds: [],
  score: { attacks: 0, caught: 0, improper: 0 },
  summary: null,
  error: null,
};

function updateRound(state: ArenaState, round: number, patch: Partial<ArenaRound>): ArenaRound[] {
  return state.rounds.map((r) => (r.round === round ? { ...r, ...patch } : r));
}

/** Folds the red-team stream into what the arena shows. The verdict comes from the API, never from here. */
export function applyEvent(state: ArenaState, event: RedTeamEvent): ArenaState {
  switch (event.type) {
    case "round_started":
      return { ...state, rounds: [...state.rounds, { round: event.round, attack: null, decision: null, caught: null }] };
    case "attack_generated":
      return { ...state, rounds: updateRound(state, event.round, { attack: event.attack ?? null }) };
    case "verdict": {
      const caught = event.caught === true;
      return {
        ...state,
        rounds: updateRound(state, event.round, { decision: event.decision ?? null, caught }),
        score: {
          attacks: state.score.attacks + 1,
          caught: state.score.caught + (caught ? 1 : 0),
          improper: state.score.improper + (caught ? 0 : 1),
        },
      };
    }
    case "summary":
      return { ...state, summary: event.message ?? null };
    case "error":
      return { ...state, error: event.message ?? "El atacante se detuvo." };
    case "round_finished":
      return state;
  }
}
