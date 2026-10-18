"use client";

import { BadgeCheck, CircleCheck, ExternalLink, LoaderCircle, RotateCw, ShieldAlert, TriangleAlert } from "lucide-react";
import { useId } from "react";
import { Freshness } from "@/components/payments/freshness";
import { Button } from "@/components/ui/button";
import type { ProofCheck, StripeProof } from "@/lib/api/client";
import { useStripeProof } from "@/lib/api/hooks";
import { formatDateTime, formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";

const SENT_CURRENCY = "USD";
export const STRIPE_UNREACHABLE = "No se pudo consultar Stripe ahora.";

const CHECK_LABEL: Record<ProofCheck["field"], string> = {
  amount: "Monto",
  currency: "Moneda",
  beneficiary: "Beneficiario (cuenta en Stripe)",
  invoice: "Factura en la metadata",
  livemode: "Modo prueba",
  reversal: "Reversado",
};

const STATE_LABEL: Record<NonNullable<StripeProof["transfer"]>["state"], string> = {
  paid: "pagada",
  partially_reversed: "reversada en parte",
  reversed: "reversada",
};

function shown(check: ProofCheck, value: string | null): string {
  if (value === null) return "—";
  if (check.field === "amount" || check.field === "reversal") return formatMoney(Number(value), SENT_CURRENCY, { decimals: 2 });
  if (check.field === "currency") return value.toUpperCase();
  if (check.field === "livemode") return value === "false" ? "sí (livemode = false)" : "no: es un pago real";
  return value;
}

function CheckRow({ check }: { check: ProofCheck }) {
  return (
    <li className="grid grid-cols-[18px_minmax(0,1fr)] gap-x-2 py-1.5 sm:grid-cols-[18px_minmax(0,11rem)_minmax(0,1fr)]">
      {check.ok ? (
        <CircleCheck aria-label="coincide" className="mt-0.5 size-4 text-pay" />
      ) : (
        <TriangleAlert aria-label="no coincide" className="mt-0.5 size-4 text-crit" />
      )}
      <span className="font-semibold">{CHECK_LABEL[check.field]}</span>
      <span className={cn("col-start-2 min-w-0 break-words sm:col-start-auto", check.ok ? "text-ink-2" : "text-crit")}>
        {check.ok ? (
          <span className="font-mono text-[12.5px]">{shown(check, check.actual)}</span>
        ) : (
          <>
            Acta: <span className="font-mono text-[12.5px]">{shown(check, check.expected)}</span> · Stripe:{" "}
            <span className="font-mono text-[12.5px]">{shown(check, check.actual)}</span>
          </>
        )}
      </span>
    </li>
  );
}

function TransferFacts({ transfer }: { transfer: NonNullable<StripeProof["transfer"]> }) {
  const balance = transfer.balance_transaction;
  const facts: [string, string][] = [
    ["Transferencia", transfer.id],
    ["Monto", formatMoney(transfer.amount, transfer.currency.toUpperCase(), { decimals: 2 })],
    ["Destino", transfer.destination ?? "—"],
    ["Creada", formatDateTime(transfer.created)],
    ["Estado", STATE_LABEL[transfer.state]],
    ["livemode", String(transfer.livemode)],
  ];
  if (balance) facts.push(["Movimiento de saldo", `${balance.id} · ${balance.status}`]);
  return (
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[13px]">
      {facts.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-ink-3">{term}</dt>
          <dd className="min-w-0 font-mono text-[12.5px] break-all">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Unreachable({ message, onRetry, retrying }: { message: string; onRetry: () => void; retrying: boolean }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-xl bg-esc-weak px-3.5 py-3 text-[14px]">
      <p className="flex gap-2">
        <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-esc" />
        {message}
      </p>
      <Button variant="outline" size="sm" disabled={retrying} onClick={onRetry}>
        <RotateCw aria-hidden /> Consultar de nuevo
      </Button>
    </div>
  );
}

function Verdict({ proof }: { proof: StripeProof }) {
  if (proof.status === "verified") {
    return (
      <p className="flex items-center gap-2 font-semibold text-pay">
        <BadgeCheck aria-hidden className="size-[18px]" /> Stripe confirma el pago tal como dice el acta
      </p>
    );
  }
  return (
    <p className="flex gap-2 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
      <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-crit" />
      {proof.message ?? "Stripe no coincide con el acta en lo marcado en rojo."}
    </p>
  );
}

function ProofBody({ proof }: { proof: StripeProof }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <Verdict proof={proof} />
        <Freshness checkedAt={proof.checked_at} />
      </div>
      {proof.checks.length ? (
        <ul aria-label="Cotejo con el acta" className="divide-y divide-line text-[13.5px]">
          {proof.checks.map((check) => (
            <CheckRow key={check.field} check={check} />
          ))}
        </ul>
      ) : null}
      {proof.transfer ? <TransferFacts transfer={proof.transfer} /> : null}
      {proof.raw ? (
        <details className="rounded-xl border border-line px-3 py-2 text-[13px]">
          <summary className="cursor-pointer font-semibold text-ink-2">Respuesta de Stripe (JSON)</summary>
          <pre className="mt-2 max-h-72 overflow-auto font-mono text-[11.5px] leading-relaxed whitespace-pre-wrap break-all text-ink-2">
            {JSON.stringify(proof.raw, null, 2)}
          </pre>
        </details>
      ) : null}
      {proof.dashboard_url ? (
        <p className="text-[13px] text-ink-3">
          <a
            href={proof.dashboard_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-semibold text-brand underline-offset-2 hover:underline"
          >
            Abrir en Stripe <ExternalLink aria-hidden className="size-3.5" />
          </a>{" "}
          · el dashboard de prueba pide iniciar sesión en la cuenta de Stripe de Blinka Keeper.
        </p>
      ) : null}
    </div>
  );
}

/** «Pago en Stripe»: what Stripe itself answers about this transfer right now, checked against the acta. */
export function StripeProofBlock({ invoiceId }: { invoiceId: string }) {
  const titleId = useId();
  const proof = useStripeProof(invoiceId, true);
  if (proof.data?.status === "not_applicable") return null;
  const retry = () => void proof.refetch();
  let body;
  if (proof.error) body = <Unreachable message={STRIPE_UNREACHABLE} onRetry={retry} retrying={proof.isFetching} />;
  else if (!proof.data)
    body = (
      <p role="status" className="flex items-center gap-2 text-[14px] text-ink-3">
        <LoaderCircle aria-hidden className="size-4 animate-spin" /> Consultando Stripe…
      </p>
    );
  else if (proof.data.status === "unavailable")
    body = <Unreachable message={proof.data.message ?? STRIPE_UNREACHABLE} onRetry={retry} retrying={proof.isFetching} />;
  else body = <ProofBody proof={proof.data} />;
  return (
    <section aria-labelledby={titleId} className="flex flex-col gap-2.5 rounded-xl border border-line px-3.5 py-3">
      <h4 id={titleId} className="eyebrow">
        Pago en Stripe
      </h4>
      {body}
    </section>
  );
}
