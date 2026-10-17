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
      return { headline: "PAGADO LEGÍTIMAMENTE", tone: "pay", note: "Era una factura válida: cumplió las doce reglas y se pagó." };
    case "pending_approval":
      return { headline: "ESCALADO", tone: "esc", note: "Custodio no pagó: le pidió permiso a una persona." };
    case "hold":
    case "rejected":
      return { headline: "FRENADO", tone: "hold", note: "Custodio no pagó: retuvo la factura." };
  }
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
