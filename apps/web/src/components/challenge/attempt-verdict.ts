/** How an attempt reads on stage: one word a room can see from the back. Display only. */
import type { ChallengeAttempt } from "@/lib/api/contracts";

export type VerdictTone = "pay" | "hold" | "esc" | "crit";

export interface AttemptVerdict {
  headline: string;
  tone: VerdictTone;
  note: string;
}

export function attemptVerdict(attempt: ChallengeAttempt): AttemptVerdict {
  if (attempt.broke_through) {
    return { headline: "PAGO INDEBIDO", tone: "crit", note: "Pasó. El auditor independiente confirmó un pago que no debía salir." };
  }
  switch (attempt.decision.status) {
    case "paid_auto":
    case "paid_human":
      return { headline: "PAGADO LEGÍTIMAMENTE", tone: "pay", note: "Era una factura válida: cumplió las quince reglas y se pagó." };
    case "pending_approval":
      return { headline: "ESCALADO", tone: "esc", note: "Blinka Keeper no pagó: le pidió permiso a una persona." };
    case "hold":
    case "rejected":
      return { headline: "FRENADO", tone: "hold", note: "Blinka Keeper no pagó: retuvo la factura." };
  }
}

/** The model that names a technique never sees the decision, so it may call a stopped attack harmless. */
const CLEARED_BY_MODEL = /sin fraude|no hay fraude|ning[uú]n|leg[ií]tim|sin ataque|no se detect/i;

/**
 * The wall's label. A stopped attempt never reads as harmless: when the model's name contradicts the
 * decision, the label names the rules that stopped it instead.
 */
export function wallLabel(attempt: ChallengeAttempt): string {
  const stoppers = attempt.decision.rules.filter((rule) => rule.outcome === "hold" || rule.outcome === "escalate");
  const technique = attempt.technique?.trim();
  if (stoppers.length === 0 || attempt.broke_through) return technique || "Técnica sin nombre";
  if (technique && !CLEARED_BY_MODEL.test(technique)) return technique;
  return `Frenado por ${spanishList(stoppers.map((rule) => rule.rule_id))}`;
}

function spanishList(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}

export const VERDICT_TEXT: Record<VerdictTone, string> = {
  pay: "text-pay",
  hold: "text-hold",
  esc: "text-esc",
  crit: "text-crit",
};

export const VERDICT_SURFACE: Record<VerdictTone, string> = {
  pay: "bg-pay-weak",
  hold: "bg-hold-weak",
  esc: "bg-esc-weak",
  crit: "bg-crit-weak",
};

export function actaHref(attempt: ChallengeAttempt): string {
  return `/panel?acta=${encodeURIComponent(attempt.decision.invoice_id)}`;
}

/** The wall is ordered by creativity; the stage wants the newest attempt on it. */
export function latestAttempt(attempts: ChallengeAttempt[]): ChallengeAttempt | null {
  return attempts.reduce<ChallengeAttempt | null>((latest, attempt) => (!latest || attempt.at > latest.at ? attempt : latest), null);
}
