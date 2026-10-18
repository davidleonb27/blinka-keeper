"use client";

import { CalendarClock, ExternalLink, RotateCcw, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import type { Decision, PaymentExecution, PaymentInstruction } from "@/lib/api/contracts";
import { formatDateTime, formatMoney } from "@/lib/format";
import { NETWORK_LABEL, RAIL_LABEL } from "@/lib/presentation";
import { StripeProofBlock } from "./stripe-proof";

/** What the Stripe rail sends is the base amount, in USD; a Blinka instruction keeps the invoiced amount and currency. */
const SENT_CURRENCY = "USD";
const ACCOUNT_DIGITS_SHOWN = 4;

interface PaymentExecutionBlockProps {
  decision: Decision;
  /** An intent from another agent is paid by that agent, so Blinka Keeper never schedules it. */
  paidByItsAgent?: boolean;
  onRetry: () => void;
  retrying: boolean;
}

function InstructionSummary({ instruction }: { instruction: PaymentInstruction }) {
  const account = instruction.account_number.slice(-ACCOUNT_DIGITS_SHOWN);
  return (
    <p className="text-[14px] text-ink-2">
      Instrucción para Blinka por {NETWORK_LABEL[instruction.network]} a {instruction.bank_name} ••{account}, con el
      acta como referencia. Blinka aún no tiene API pública: no se envió y no se movió dinero.
    </p>
  );
}

function Outcome({
  execution,
  onRetry,
  retrying,
}: { execution: PaymentExecution } & Omit<PaymentExecutionBlockProps, "decision" | "paidByItsAgent">) {
  if (execution.status === "failed") {
    return (
      <div className="flex flex-col items-start gap-2.5">
        <p className="flex gap-2 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
          <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-crit" />
          No salió: {execution.error ?? "el riel no confirmó el pago."}
        </p>
        <Button variant="outline" size="sm" disabled={retrying} onClick={onRetry}>
          <RotateCcw aria-hidden /> Reintentar pago
        </Button>
      </div>
    );
  }
  if (execution.status === "simulated") {
    if (execution.instruction) return <InstructionSummary instruction={execution.instruction} />;
    return <p className="text-[14px] text-ink-2">Quedó registrado sin riel real; no se movió dinero.</p>;
  }
  return (
    <p className="text-[14px] text-ink-2">
      Transferencia{" "}
      {execution.dashboard_url ? (
        <a
          href={execution.dashboard_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-[13px] font-semibold text-brand underline-offset-2 hover:underline"
        >
          {execution.external_id} <ExternalLink aria-hidden className="size-3.5" />
        </a>
      ) : (
        <code className="font-mono text-[13px]">{execution.external_id}</code>
      )}
    </p>
  );
}

function sentByStripe(execution: PaymentExecution): boolean {
  return execution.rail === "stripe_test" && execution.status === "executed" && Boolean(execution.external_id);
}

const PAID: ReadonlySet<Decision["status"]> = new Set(["paid_auto", "paid_human"]);

function Scheduled({ titleId, decision }: { titleId: string; decision: Decision }) {
  return (
    <section aria-labelledby={titleId}>
      <h3 id={titleId} className="eyebrow mb-2.5">
        Ejecución del pago
      </h3>
      <p className="flex flex-wrap items-center gap-1.5 rounded-xl border border-line px-3.5 py-3 text-[14px] text-ink-2">
        <CalendarClock aria-hidden className="size-4 text-brand" />
        Programado: {formatMoney(decision.amount_base, SENT_CURRENCY)} salen el día que corresponde, no antes.
        <Link href="/calendario" className="font-semibold text-brand hover:underline">
          Ver en el calendario
        </Link>
      </p>
    </section>
  );
}

export function PaymentExecutionBlock({ decision, paidByItsAgent = false, onRetry, retrying }: PaymentExecutionBlockProps) {
  const titleId = useId();
  const { execution } = decision;
  if (!execution) {
    const scheduled = PAID.has(decision.status) && !paidByItsAgent;
    return scheduled ? <Scheduled titleId={titleId} decision={decision} /> : null;
  }
  const amount = execution.instruction
    ? formatMoney(execution.instruction.amount, execution.instruction.currency)
    : formatMoney(decision.amount_base, SENT_CURRENCY);
  return (
    <section aria-labelledby={titleId}>
      <h3 id={titleId} className="eyebrow mb-2.5">
        Ejecución del pago
      </h3>
      <div className="flex flex-col gap-2.5 rounded-xl border border-line px-3.5 py-3">
        <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[13px] text-ink-3">
          <span className="font-semibold text-ink">{RAIL_LABEL[execution.rail]}</span>
          <span className="tabular">
            {execution.status === "executed" ? "enviado" : "monto"} {amount}
          </span>
          <span>{formatDateTime(execution.executed_at)}</span>
        </p>
        <Outcome execution={execution} onRetry={onRetry} retrying={retrying} />
      </div>
      {sentByStripe(execution) ? (
        <div className="mt-2.5">
          <StripeProofBlock invoiceId={decision.invoice_id} />
        </div>
      ) : null}
    </section>
  );
}
