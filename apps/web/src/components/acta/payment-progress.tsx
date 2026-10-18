"use client";

import { CalendarClock, CircleCheck, LoaderCircle, ShieldAlert } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import type { Decision, PaymentRailName } from "@/lib/api/contracts";
import { cn } from "@/lib/utils";

/** What the person sees between «Aprobar pago» and the receipt: the request in flight, then what the rail answered. */
export type PaymentStep = { phase: "sending"; rail: PaymentRailName | null } | { phase: "done"; decision: Decision };

const SENDING_LABEL: Record<PaymentRailName, string> = {
  stripe_test: "Enviando a Stripe…",
  blinka_simulated: "Armando la instrucción para Blinka…",
  simulated: "Registrando el pago…",
};
const PAID: ReadonlySet<Decision["status"]> = new Set(["paid_auto", "paid_human"]);

interface Line {
  key: string;
  tone: "busy" | "pay" | "crit" | "neutral";
  icon: ReactNode;
  text: ReactNode;
}

function lineOf(step: PaymentStep): Line | null {
  if (step.phase === "sending") {
    const text = step.rail ? SENDING_LABEL[step.rail] : "Enviando el pago…";
    return { key: "sending", tone: "busy", icon: <LoaderCircle aria-hidden className="size-4 animate-spin" />, text };
  }
  const { decision } = step;
  const execution = decision.execution;
  if (!PAID.has(decision.status)) return null;
  if (!execution) {
    const text = "Aprobado · sale el día que vence, no antes";
    return { key: "scheduled", tone: "neutral", icon: <CalendarClock aria-hidden className="size-4" />, text };
  }
  if (execution.status === "failed") {
    const text = `No salió: ${execution.error ?? "el riel no confirmó el pago."}`;
    return { key: "failed", tone: "crit", icon: <ShieldAlert aria-hidden className="size-4" />, text };
  }
  const text =
    execution.status === "executed" && execution.external_id ? (
      <>
        Pagado · <code className="font-mono text-[13px]">{execution.external_id}</code>
      </>
    ) : (
      "Pagado · simulado, no se movió dinero"
    );
  return { key: "paid", tone: "pay", icon: <CircleCheck aria-hidden className="size-4" />, text };
}

const TONE_CLASS: Record<Line["tone"], string> = {
  busy: "bg-surface-2 text-ink-2",
  pay: "bg-pay-weak text-pay",
  crit: "bg-crit-weak text-crit",
  neutral: "bg-surface-2 text-ink-2",
};

export function PaymentProgress({ step }: { step: PaymentStep | null }) {
  const reduceMotion = useReducedMotion();
  const line = step ? lineOf(step) : null;
  return (
    <div aria-live="polite" aria-label="Estado del pago">
      <AnimatePresence mode="wait" initial={false}>
        {line ? (
          <motion.p
            key={line.key}
            initial={reduceMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: -4 }}
            className={cn("flex items-center gap-2 rounded-xl px-3.5 py-3 text-[14px] font-semibold", TONE_CLASS[line.tone])}
          >
            {line.icon}
            <span className="min-w-0 break-words">{line.text}</span>
          </motion.p>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
