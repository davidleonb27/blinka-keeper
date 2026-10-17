"use client";

import { ArrowRight, ShieldCheck } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useEffect } from "react";
import { Seal } from "@/components/brand/seal";
import { StatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/errors";
import { useCompleteOnboarding } from "@/lib/api/hooks";
import { browserWorkspaceStore } from "@/lib/api/workspace";
import { formatDate } from "@/lib/format";
import { amountText, mainReason, supplierText } from "@/lib/presentation";
import type { StepProps } from "./basic-steps";
import { StepFrame } from "./step-frame";
import { onboardingRequest } from "./state";

const STAGGER_S = 0.12;

export function SimulationStep({ answers, update, frame }: StepProps) {
  const complete = useCompleteOnboarding();
  const reduceMotion = useReducedMotion();
  const { mutate, status } = complete;
  const result = answers.result;

  useEffect(() => {
    if (result || status !== "idle") return;
    mutate(onboardingRequest(answers), {
      onSuccess: (done) => {
        browserWorkspaceStore.write(done);
        update({ result: done });
      },
    });
  }, [answers, mutate, result, status, update]);

  const metrics = result?.metrics;
  return (
    <StepFrame
      {...frame}
      busy={!result && !complete.error}
      busyLabel="Decidiendo tu primera semana…"
      title="Tu primera semana, decidida"
      helper="Custodio pasó una semana de facturas de ejemplo por tus reglas, con trampas incluidas. Así se habría comportado."
    >
      {complete.error ? <p className="text-[13.5px] text-crit">{messageOf(complete.error)}</p> : null}
      {result && metrics ? (
        <div className="flex flex-col gap-3">
          <p className="flex flex-wrap items-center gap-2 rounded-2xl bg-pay-weak px-4 py-3 text-[15px]">
            <ShieldCheck aria-hidden className="size-5 text-pay" />
            <span>
              <b>{metrics.total} facturas decididas</b>: {metrics.paid_auto} pagadas solas, {metrics.hold} retenidas y{" "}
              {metrics.pending} esperan tu aprobación. Pagos indebidos: <b>{metrics.improper_payments}</b>.
            </span>
          </p>
          <ul className="card-surface divide-y divide-line p-1.5">
            {result.first_week.map((item, index) => (
              <motion.li
                key={item.decision.invoice_id}
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * STAGGER_S }}
                className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-3 py-2.5"
              >
                <span className="min-w-0">
                  <b className="block truncate font-semibold">{supplierText(item.decision)}</b>
                  <span className="block truncate text-[12.5px] text-ink-3">
                    {mainReason(item.decision)} · {formatDate(item.received_at)}
                  </span>
                </span>
                <span className="flex flex-col items-end gap-1">
                  <span className="text-[13px] font-semibold tabular">{amountText(item.decision)}</span>
                  <StatusPill status={item.decision.status} />
                </span>
              </motion.li>
            ))}
          </ul>
        </div>
      ) : null}
    </StepFrame>
  );
}

export function ReadyStep({ answers }: Pick<StepProps, "answers">) {
  const name = answers.profile?.company_name ?? answers.companyName;
  const approvers = answers.approvers.filter((a) => a.name.trim()).length;
  return (
    <div className="flex flex-col items-start gap-7">
      <Seal className="size-16" />
      <div>
        <h1 className="font-display text-[34px] leading-[1.05] font-semibold tracking-[-0.025em] sm:text-[44px]">
          Custodio está listo
        </h1>
        <p className="mt-3 max-w-[54ch] text-base text-ink-2">
          {name} ya tiene reglas, {answers.suppliers.length} beneficiarios permitidos y {approvers}{" "}
          {approvers === 1 ? "persona que aprueba" : "personas que aprueban"}. Lo que cumpla las reglas se paga solo; lo
          demás espera tu sí, y todo queda en el registro.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button asChild size="lg">
          {/* Autofocus keeps the Enter-advances promise: Enter follows the link. */}
          <Link href="/panel" autoFocus>
            Ir al panel <ArrowRight aria-hidden />
          </Link>
        </Button>
        <Button asChild variant="ghost" size="lg">
          <Link href="/reglas">Revisar las reglas</Link>
        </Button>
      </div>
    </div>
  );
}
