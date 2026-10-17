"use client";

import { ExternalLink, RotateCcw, ShieldAlert } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import type { Decision, PaymentExecution } from "@/lib/api/contracts";
import { formatDateTime, formatMoney } from "@/lib/format";
import { RAIL_LABEL } from "@/lib/presentation";

/** What the rail sends is the base amount, in USD; the invoiced amount and currency are in the header. */
const SENT_CURRENCY = "USD";

interface PaymentExecutionBlockProps {
  decision: Decision;
  onRetry: () => void;
  retrying: boolean;
}

function Outcome({ execution, onRetry, retrying }: { execution: PaymentExecution } & Omit<PaymentExecutionBlockProps, "decision">) {
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

export function PaymentExecutionBlock({ decision, onRetry, retrying }: PaymentExecutionBlockProps) {
  const titleId = useId();
  const { execution } = decision;
  if (!execution) return null;
  return (
    <section aria-labelledby={titleId}>
      <h3 id={titleId} className="eyebrow mb-2.5">
        Ejecución del pago
      </h3>
      <div className="flex flex-col gap-2.5 rounded-xl border border-line px-3.5 py-3">
        <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[13px] text-ink-3">
          <span className="font-semibold text-ink">{RAIL_LABEL[execution.rail]}</span>
          <span className="tabular">
            {execution.status === "executed" ? "enviado" : "monto"} {formatMoney(decision.amount_base, SENT_CURRENCY)}
          </span>
          <span>{formatDateTime(execution.executed_at)}</span>
        </p>
        <Outcome execution={execution} onRetry={onRetry} retrying={retrying} />
      </div>
    </section>
  );
}
