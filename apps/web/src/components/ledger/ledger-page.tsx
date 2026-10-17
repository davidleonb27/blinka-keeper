"use client";

import { CircleCheck, CircleX, Hammer, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import type { LedgerEntry, LedgerKind, LedgerVerification } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useLedger, useTamperDemo, useVerifyLedger } from "@/lib/api/hooks";
import { formatDateTime, shortHash } from "@/lib/format";
import { isDecisionStatus, STATUS_META } from "@/lib/presentation";
import { cn } from "@/lib/utils";

const KIND_LABEL: Record<LedgerKind, string> = {
  policy_changed: "Reglas",
  invoice_received: "Factura recibida",
  decision: "Decisión",
  approval: "Aprobación",
  payment: "Pago",
  redteam_attack: "Ataque del red team",
  challenge_attempt: "Intento del reto",
  intent: "Intención de otro agente",
  reconciliation: "Conciliación bancaria",
  reconciliation_review: "Revisión de un movimiento",
  period_closed: "Cierre del mes",
};
// Reconciliations and closes are about a statement or a month, not an invoice: they have no acta to open.
const WITHOUT_ACTA = new Set<LedgerKind>(["reconciliation_review", "period_closed"]);

/** A reconciliation's own entry names its statement; the ones that confirm a payment name the invoice. */
function isReconciliationId(entry: LedgerEntry): boolean {
  return entry.kind === "reconciliation" && "statement_sha256" in entry.payload;
}

function statusLabel(status: unknown): string | null {
  return isDecisionStatus(status) ? STATUS_META[status].label : null;
}

function textOf(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function approverOf(approval: unknown): string | null {
  return approval && typeof approval === "object" && "approver" in approval ? textOf(approval.approver) : null;
}

/** Who and what, from the payload fields the API writes for each kind of entry. */
function payloadSummary(entry: LedgerEntry): string {
  const { actor, summary, status, supplier, invoice_number: number, version, approval } = entry.payload;
  const who = textOf(actor) ?? approverOf(approval) ?? textOf(supplier);
  const what =
    textOf(summary) ?? statusLabel(status) ?? textOf(number) ?? (typeof version === "number" ? `versión ${version}` : null);
  return [who, what].filter((part): part is string => part !== null).join(" · ");
}

function VerificationBanner({ result, copy }: { result: LedgerVerification; copy: boolean }) {
  return result.valid ? (
    <p className="flex items-center gap-2.5 rounded-xl bg-pay-weak px-3.5 py-3 text-[14px]">
      <CircleCheck aria-hidden className="size-5 shrink-0 text-pay" />
      La cadena está íntegra: {result.length} asientos, cada uno enlazado al anterior.
    </p>
  ) : (
    <p className="flex items-center gap-2.5 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
      <CircleX aria-hidden className="size-5 shrink-0 text-crit" />
      {copy ? "En la copia alterada" : "En el registro"}, la cadena se rompe en el asiento #{result.first_broken_seq}: su hash ya no
      corresponde a su contenido. {copy ? "El registro real no se tocó." : ""}
    </p>
  );
}

function LedgerTable({ entries, brokenSeq }: { entries: LedgerEntry[]; brokenSeq: number | null }) {
  return (
    <ol className="divide-y divide-line">
      {entries.toReversed().map((entry) => (
        <li
          key={entry.seq}
          className={cn(
            "grid grid-cols-[48px_minmax(0,1fr)] gap-x-3 gap-y-1 px-2 py-3 sm:grid-cols-[56px_150px_minmax(0,1fr)_auto]",
            entry.seq === brokenSeq && "rounded-lg bg-crit-weak",
          )}
        >
          <span className="font-mono text-[12px] text-ink-3 tabular">#{entry.seq}</span>
          <span className="font-semibold">
            {KIND_LABEL[entry.kind]}
            {entry.seq === brokenSeq ? <span className="ml-2 text-xs font-semibold text-crit">alterado en la copia</span> : null}
          </span>
          <span className="col-start-2 min-w-0 text-[13px] text-ink-2 sm:col-start-auto">
            {entry.subject_id && !WITHOUT_ACTA.has(entry.kind) && !isReconciliationId(entry) ? (
              <Link href={`/panel?acta=${entry.subject_id}`} className="font-mono text-[12.5px] text-brand hover:underline">
                {entry.subject_id}
              </Link>
            ) : null}{" "}
            <span className="break-words">{payloadSummary(entry)}</span>
            <span className="block text-xs text-ink-3">{formatDateTime(entry.at)}</span>
          </span>
          <span className="col-start-2 font-mono text-[11.5px] text-ink-3 sm:col-start-auto sm:text-right">
            <span className="sr-only">hash </span>
            {shortHash(entry.hash)}
            <span className="block">
              <span className="sr-only">anterior </span>← {shortHash(entry.prev_hash)}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export function LedgerPage() {
  const ledger = useLedger();
  const verify = useVerifyLedger();
  const tamper = useTamperDemo();

  return (
    <>
      <PageHeader
        title="Registro"
        subtitle="Cada decisión queda encadenada a la anterior con SHA-256. Si alguien cambia un asiento, la verificación dice exactamente dónde."
      />
      <section className="card-surface mb-4 flex flex-col gap-3 p-5" aria-label="Verificación">
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => verify.mutate()} disabled={verify.isPending}>
            <ShieldCheck aria-hidden /> Verificar la cadena
          </Button>
          <Button variant="reject" onClick={() => tamper.mutate()} disabled={tamper.isPending}>
            <Hammer aria-hidden /> Alterar una copia
          </Button>
        </div>
        <div aria-live="polite" className="flex flex-col gap-2">
          {verify.data ? <VerificationBanner result={verify.data} copy={false} /> : null}
          {tamper.data ? <VerificationBanner result={tamper.data.tampered} copy /> : null}
          {verify.error || tamper.error ? <p role="alert" className="text-crit">{messageOf(verify.error ?? tamper.error)}</p> : null}
        </div>
        <p className="text-[12.5px] text-ink-3">
          hash = sha256(hash anterior + JSON canónico del asiento). El primer asiento parte de 64 ceros.
        </p>
      </section>
      {ledger.error ? <ErrorState error={ledger.error} onRetry={() => void ledger.refetch()} /> : null}
      {ledger.data ? (
        <section className="card-surface p-2 sm:p-3" aria-label="Asientos del registro">
          <LedgerTable entries={ledger.data} brokenSeq={tamper.data?.altered_seq ?? null} />
        </section>
      ) : !ledger.error ? (
        <LoadingBlock className="h-72" />
      ) : null}
    </>
  );
}
