"use client";

import { ArrowLeftRight, CircleCheck, Download, ExternalLink, FileCode2, RotateCw, Send, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";
import { toast } from "sonner";
import { ActaDrawer } from "@/components/acta/acta-drawer";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { StatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";
import { useApi } from "@/components/providers/api-provider";
import type { PaymentListRow, PaymentsOverview, RailMatchLine, RailMatchView } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { usePayments } from "@/lib/api/hooks";
import { saveFile } from "@/lib/download";
import { formatCount, formatMoney } from "@/lib/format";
import { RAIL_LABEL } from "@/lib/presentation";
import { cn } from "@/lib/utils";
import { Freshness } from "./freshness";

const SENT_CURRENCY = "USD";
const PAIN001_FILE = "custodio-pain.001.001.09.xml";
export const READY_FOR_BLINKA = "Listo para que Blinka lo pague";

const LINE_LABEL: Record<RailMatchLine["kind"], string> = {
  matched: "Cuadra",
  amount_differs: "Monto distinto",
  missing_in_stripe: "Falta en Stripe",
  missing_in_registry: "No está en el registro",
};

function usd(amount: number | null | undefined): string {
  return formatMoney(amount, SENT_CURRENCY, { decimals: 2 });
}

function actaHref(invoiceId: string): string {
  return `/pagos?acta=${encodeURIComponent(invoiceId)}`;
}

function MatchBanner({ match }: { match: RailMatchView }) {
  const lines = match.lines.length;
  if (match.status === "balanced") {
    return (
      <p className="flex gap-2 rounded-xl bg-pay-weak px-3.5 py-3 text-[14px] font-semibold text-pay">
        <CircleCheck aria-hidden className="mt-0.5 size-4 shrink-0" />
        Cuadra: {formatCount(lines)} pagos del registro, {formatCount(lines)} transferencias en Stripe, el mismo monto cada una.
      </p>
    );
  }
  if (match.status === "differences") {
    const off = match.lines.filter((line) => line.kind !== "matched").length;
    return (
      <p className="flex gap-2 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px] font-semibold text-crit">
        <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
        No cuadra: {formatCount(off)} {off === 1 ? "diferencia" : "diferencias"} entre el registro de Blinka Keeper y Stripe.
        {match.message ? ` ${match.message}` : ""}
      </p>
    );
  }
  const tone = match.status === "unavailable" ? "bg-esc-weak" : "bg-surface-2 text-ink-2";
  return <p className={cn("rounded-xl px-3.5 py-3 text-[14px]", tone)}>{match.message}</p>;
}

function Totals({ match }: { match: RailMatchView }) {
  const shown = match.status === "balanced" || match.status === "differences";
  const items = [
    { label: "Registro de Blinka Keeper", value: usd(match.recorded_total), bad: false },
    { label: "Stripe", value: shown ? usd(match.stripe_total) : "—", bad: false },
    { label: "Diferencia", value: shown ? usd(match.difference) : "—", bad: shown && match.difference !== 0 },
  ];
  return (
    <dl className="grid grid-cols-1 gap-2 sm:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className={cn(
            "flex min-w-0 items-baseline justify-between gap-3 rounded-xl border border-line px-3 py-2.5 sm:block",
            item.bad && "border-crit bg-crit-weak",
          )}
        >
          <dt className="text-[12px] text-ink-3">{item.label}</dt>
          <dd className={cn("text-[15px] font-semibold whitespace-nowrap tabular", item.bad && "text-crit")}>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function MatchRow({ line }: { line: RailMatchLine }) {
  const ok = line.kind === "matched";
  return (
    <li className={cn("grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-3 gap-y-1 px-2 py-2.5", !ok && "rounded-lg bg-crit-weak")}>
      <div className="min-w-0">
        <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span className={cn("text-[12.5px] font-semibold", ok ? "text-pay" : "text-crit")}>{LINE_LABEL[line.kind]}</span>
          {line.invoice_id ? (
            <Link href={actaHref(line.invoice_id)} scroll={false} className="font-mono text-[12.5px] text-brand hover:underline">
              {line.invoice_id}
            </Link>
          ) : null}
          {line.supplier_name ? <span className="truncate text-[13px]">{line.supplier_name}</span> : null}
        </p>
        <a
          href={line.dashboard_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 font-mono text-[12px] break-all text-ink-3 hover:text-brand"
        >
          {line.transfer_id} <ExternalLink aria-hidden className="size-3" />
        </a>
      </div>
      <div className="text-right text-[13px] tabular">
        <span className="block">Blinka Keeper {usd(line.recorded_amount)}</span>
        <span className={cn("block", ok ? "text-ink-3" : "font-semibold text-crit")}>Stripe {usd(line.stripe_amount)}</span>
      </div>
    </li>
  );
}

function MatchCard({ match, onRefresh, refreshing }: { match: RailMatchView; onRefresh: () => void; refreshing: boolean }) {
  return (
    <section aria-labelledby="cuadre-stripe" className="card-surface flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="cuadre-stripe" className="flex items-center gap-2 font-semibold">
          <ArrowLeftRight aria-hidden className="size-4 text-brand" /> Registro de Blinka Keeper ↔ Stripe
        </h2>
        <span className="flex items-center gap-2">
          {match.status === "balanced" || match.status === "differences" ? (
            <Freshness checkedAt={match.checked_at} label="Consultado en Stripe" />
          ) : null}
          <Button variant="outline" size="sm" onClick={onRefresh} disabled={refreshing}>
            <RotateCw aria-hidden /> Consultar
          </Button>
        </span>
      </div>
      <MatchBanner match={match} />
      <Totals match={match} />
      {match.lines.length ? (
        <ul aria-label="Cuadre por transferencia" className="flex flex-col divide-y divide-line">
          {match.lines.map((line) => (
            <MatchRow key={`${line.kind}-${line.transfer_id}-${line.invoice_id ?? ""}`} line={line} />
          ))}
        </ul>
      ) : null}
      <p className="text-xs text-ink-3">
        Cada pago del registro debe tener exactamente una transferencia en Stripe con el mismo monto, y cada transferencia de
        este espacio en Stripe, su pago en el registro. Montos en USD, la moneda que envía el riel.
      </p>
    </section>
  );
}

function ExportCard({ overview }: { overview: PaymentsOverview }) {
  const api = useApi();
  const count = overview.exportable;
  async function download() {
    try {
      saveFile(await api.downloadPain001(), PAIN001_FILE);
      toast.success(`Archivo para Blinka con ${formatCount(count)} pagos.`);
    } catch (error) {
      toast.error(messageOf(error));
    }
  }
  return (
    <section aria-labelledby="archivo-blinka" className="card-surface flex flex-col gap-2.5 p-5">
      <h2 id="archivo-blinka" className="flex items-center gap-2 font-semibold">
        <FileCode2 aria-hidden className="size-4 text-brand" /> Archivo para Blinka
      </h2>
      <p className="text-[14px] text-ink-2">
        Los {formatCount(count)} pagos aprobados del lote como ISO 20022 <b>pain.001.001.09</b>: la empresa como deudor y
        cada proveedor con su cuenta registrada, validado contra el esquema oficial.{" "}
        <b className="text-ink">{READY_FOR_BLINKA}.</b>
      </p>
      <div>
        <Button onClick={() => void download()} disabled={count === 0}>
          <Download aria-hidden /> Descargar pain.001
        </Button>
      </div>
    </section>
  );
}

function ExecutionText({ payment }: { payment: PaymentListRow }) {
  const execution = payment.execution;
  if (!execution) return <span className="text-ink-3">Programado: sale el día que vence</span>;
  const rail = RAIL_LABEL[execution.rail];
  if (execution.status === "failed") return <span className="text-crit">{rail} · no salió</span>;
  if (execution.status === "simulated") return <span className="text-ink-3">{rail} · no se movió dinero</span>;
  return (
    <span className="text-ink-2">
      {rail} ·{" "}
      {execution.dashboard_url ? (
        <a href={execution.dashboard_url} target="_blank" rel="noreferrer" className="font-mono text-[12px] break-all text-brand hover:underline">
          {execution.external_id}
        </a>
      ) : (
        <code className="font-mono text-[12px]">{execution.external_id}</code>
      )}
    </span>
  );
}

function PaymentsList({ overview }: { overview: PaymentsOverview }) {
  return (
    <section aria-labelledby="pagos-del-espacio" className="card-surface p-5">
      <h2 id="pagos-del-espacio" className="flex items-center gap-2 font-semibold">
        <Send aria-hidden className="size-4 text-brand" /> Pagos del espacio
      </h2>
      {overview.payments.length ? (
        <ul className="mt-2 divide-y divide-line">
          {overview.payments.map((payment) => (
            <li key={payment.invoice_id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-1 px-2 py-3">
              <div className="min-w-0">
                <p className="font-semibold break-words">
                  {payment.supplier_name ?? "Proveedor sin leer"}
                  <Link
                    href={actaHref(payment.invoice_id)}
                    scroll={false}
                    className="ml-2 font-mono text-[12px] font-normal text-brand hover:underline"
                  >
                    {payment.invoice_id}
                  </Link>
                </p>
                <p className="text-[13px]">
                  <ExecutionText payment={payment} />
                </p>
              </div>
              <span className="flex flex-col items-end gap-1">
                <strong className="tabular">{formatMoney(payment.amount, payment.currency)}</strong>
                <StatusPill status={payment.status} />
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-ink-2">
          Aún no hay pagos. <Link href="/panel" className="font-semibold text-brand hover:underline">Decide las facturas en el panel</Link>.
        </p>
      )}
    </section>
  );
}

export function PaymentsPage() {
  const payments = usePayments();
  const overview = payments.data;
  return (
    <>
      <PageHeader
        title="Pagos"
        subtitle="Lo que Blinka Keeper pagó, comprobado en vivo contra Stripe transferencia por transferencia, y el archivo para que Blinka pague el lote."
      />
      {payments.isPending ? <LoadingBlock label="Consultando los pagos…" /> : null}
      {payments.error ? <ErrorState error={payments.error} onRetry={() => void payments.refetch()} /> : null}
      {overview ? (
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <MatchCard match={overview.stripe} onRefresh={() => void payments.refetch()} refreshing={payments.isFetching} />
            <ExportCard overview={overview} />
          </div>
          <PaymentsList overview={overview} />
        </div>
      ) : null}
      {/* Only the drawer reads the URL, so only it waits for the browser: the page itself is prerendered. */}
      <Suspense>
        <ActaDrawer />
      </Suspense>
    </>
  );
}
