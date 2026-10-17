"use client";

import { ExternalLink, FileText } from "lucide-react";
import Link from "next/link";
import { useId, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { MovementView } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useResolveMovement } from "@/lib/api/hooks";
import { formatDate, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { LEVEL_LABEL, STATUS_LABEL } from "./labels";

const TONE = {
  reconciled: "bg-pay-weak text-pay",
  reconciled_with_difference: "bg-esc-weak text-ink",
  bank_fee: "bg-surface-2 text-ink-2",
  unmatched_outflow: "bg-crit-weak text-crit",
  duplicate: "bg-hold-weak text-hold",
  unread: "bg-crit-weak text-crit",
  inflow: "bg-surface-2 text-ink-2",
} as const;

function Badge({ children, className }: { children: string; className?: string }) {
  return (
    <span className={cn("inline-flex h-6 items-center rounded-full px-2 text-[11.5px] font-semibold", className)}>
      {children}
    </span>
  );
}

function ReviewForm({ reconciliationId, item }: { reconciliationId: string; item: MovementView }) {
  const resolve = useResolveMovement(reconciliationId);
  const [note, setNote] = useState("");
  const [reviewer, setReviewer] = useState("");
  const noteId = useId();
  const reviewerId = useId();

  function submit(event: FormEvent) {
    event.preventDefault();
    resolve.mutate({ movement_id: item.movement.id, reviewer: reviewer.trim(), note: note.trim() });
  }

  return (
    <form aria-label={`Revisar fila ${item.movement.row}`} onSubmit={submit} className="mt-2 flex flex-col gap-2">
      <label htmlFor={noteId} className="text-[12.5px] text-ink-2">
        Nota de revisión
      </label>
      <textarea
        id={noteId}
        rows={2}
        value={note}
        maxLength={500}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Qué es este movimiento y qué se hizo"
        className="w-full resize-y rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2 text-[13px]"
      />
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex min-w-[160px] flex-1 flex-col gap-1">
          <label htmlFor={reviewerId} className="text-[12.5px] text-ink-2">
            Quién revisa
          </label>
          <Input id={reviewerId} value={reviewer} maxLength={120} onChange={(e) => setReviewer(e.target.value)} />
        </div>
        <Button type="submit" size="sm" disabled={resolve.isPending || !note.trim() || !reviewer.trim()}>
          Marcar como revisado
        </Button>
      </div>
      {resolve.error ? (
        <p role="alert" className="text-[12.5px] text-crit">
          {messageOf(resolve.error)}
        </p>
      ) : null}
    </form>
  );
}

export function MovementCard({ reconciliationId, item }: { reconciliationId: string; item: MovementView }) {
  const { movement, result, review } = item;
  return (
    <li className="flex flex-col gap-1.5 border-b border-line py-3 last:border-b-0">
      <div className="flex items-start justify-between gap-3">
        <span className="min-w-0 font-semibold break-words">{movement.description}</span>
        <span className="shrink-0 font-semibold tabular">
          {movement.amount === null ? "NO LEÍDO" : formatMoney(movement.amount, movement.currency, { decimals: 2 })}
        </span>
      </div>
      <span className="text-xs text-ink-3">
        {movement.booked_on ? formatDate(movement.booked_on) : "Sin fecha leída"} · fila {movement.row}
        {movement.reference ? ` · ref. ${movement.reference}` : ""}
      </span>
      <div className="flex flex-wrap gap-1.5">
        <Badge className={TONE[result.status]}>{STATUS_LABEL[result.status]}</Badge>
        {result.level ? <Badge className="bg-brand-weak text-ink">{LEVEL_LABEL[result.level]}</Badge> : null}
        {result.difference !== null && result.difference !== undefined ? (
          <Badge className="bg-surface-2 text-ink-2">
            {`Diferencia ${formatMoney(result.difference, movement.currency, { decimals: 2 })}`}
          </Badge>
        ) : null}
      </div>
      <p className="text-[13px] text-ink-2">{result.reason}</p>
      {result.invoice_id || item.external_id ? (
        <div className="flex flex-wrap gap-3 text-[12.5px]">
          {result.invoice_id ? (
            <Link href={`/panel?acta=${result.invoice_id}`} className="inline-flex items-center gap-1 text-brand hover:underline">
              <FileText aria-hidden className="size-3.5" /> Acta {result.invoice_id}
            </Link>
          ) : null}
          {item.external_id ? (
            item.dashboard_url ? (
              <a
                href={item.dashboard_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 font-mono text-brand hover:underline"
              >
                {item.external_id} <ExternalLink aria-hidden className="size-3.5" />
              </a>
            ) : (
              <span className="font-mono text-ink-3">{item.external_id}</span>
            )
          ) : null}
        </div>
      ) : null}
      {review ? (
        <p className="rounded-lg bg-pay-weak px-2.5 py-2 text-[13px]">
          Revisó {review.reviewer} (asiento #{review.ledger_seq}): {review.note}
        </p>
      ) : item.needs_review ? (
        <ReviewForm reconciliationId={reconciliationId} item={item} />
      ) : null}
    </li>
  );
}
