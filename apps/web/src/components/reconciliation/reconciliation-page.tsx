"use client";

import { Download, FileUp, Landmark, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useId, useState, type DragEvent, type ReactNode } from "react";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApi } from "@/components/providers/api-provider";
import type { DemoStatementFormat, ReconciliationView, StatementInput } from "@/lib/api/client";
import type { MovementView, Tally } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useClosePeriod, useReconcileStatement, useReconciliation, useReconciliations } from "@/lib/api/hooks";
import { saveFile } from "@/lib/download";
import { formatDateTime, formatMoney, formatNumber, shortHash } from "@/lib/format";
import { cn } from "@/lib/utils";
import { counted, monthOf } from "./labels";
import { MovementCard } from "./movement-card";

const ACCEPTED = ".csv,.pdf,.png,.jpg,.jpeg,.webp,text/csv,application/pdf,image/png,image/jpeg,image/webp";
const DIFFERENCE_COLUMN = new Set(["reconciled_with_difference", "bank_fee"]);

function StatementDrop({ onReconcile, pending }: { onReconcile: (input: StatementInput) => void; pending: boolean }) {
  const api = useApi();
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const [downloadError, setDownloadError] = useState<unknown>(null);

  function drop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) onReconcile({ file });
  }

  async function download(format: DemoStatementFormat) {
    setDownloadError(null);
    try {
      saveFile(await api.downloadDemoStatement(format), `extracto-demo.${format}`);
    } catch (error) {
      setDownloadError(error);
    }
  }

  return (
    <section className="card-surface mb-4 flex flex-col gap-3 p-5" aria-label="Extracto">
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
        className={cn(
          "flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed border-line-2 px-4 py-6 text-center focus-within:border-brand hover:border-brand",
          dragging && "border-brand bg-brand-weak",
        )}
      >
        <FileUp aria-hidden className="size-6 text-brand" />
        <span className="font-semibold">Arrastra el extracto del banco aquí o elígelo</span>
        <span className="max-w-[60ch] text-[13px] text-ink-2">
          CSV: lo lee el código. PDF o imagen: lo lee Claude y el código verifica cada fila contra el documento; lo que
          no se puede leer queda como NO LEÍDO, nunca inventado. Hasta 4 MB.
        </span>
        <input
          id={inputId}
          type="file"
          accept={ACCEPTED}
          className="sr-only"
          disabled={pending}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onReconcile({ file });
            event.target.value = "";
          }}
        />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => onReconcile({ demo: true })} disabled={pending}>
          <Landmark aria-hidden /> Usar extracto de demo
        </Button>
        <span className="text-[13px] text-ink-3">o descárgalo:</span>
        <Button variant="ghost" size="sm" aria-label="Descargar el extracto de demo en CSV" onClick={() => void download("csv")}>
          CSV
        </Button>
        <Button variant="ghost" size="sm" aria-label="Descargar el extracto de demo en PDF" onClick={() => void download("pdf")}>
          PDF
        </Button>
      </div>
      <div aria-live="polite">
        {pending ? <p role="status">Leyendo y conciliando el extracto…</p> : null}
        {downloadError ? (
          <p role="alert" className="text-[13px] text-crit">
            {messageOf(downloadError)}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function Figure({ label, tally, currency, unit }: { label: string; tally: Tally; currency: string; unit: [string, string] }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-xl bg-surface-2 px-3 py-2.5">
      <span className="text-[12.5px] text-ink-2">{label}</span>
      <b className="tabular">{formatMoney(tally.total, currency)}</b>
      <span className="text-xs text-ink-3">{counted(tally.count, ...unit)}</span>
    </div>
  );
}

function Overview({ view }: { view: ReconciliationView }) {
  const { summary, settings, currency } = view;
  return (
    <section className="card-surface mb-4 flex flex-col gap-3 p-5" aria-label="Resumen de la conciliación">
      <div>
        <h2 className="font-display text-[19px] font-semibold">Extracto de {monthOf(view.period)}</h2>
        <p className="text-[13px] text-ink-2">
          {view.filename} · leído por {view.reader} · {counted(view.movements.length, "movimiento", "movimientos")} ·
          tolerancia de cambio ±{formatNumber(settings.fx_tolerance_pct, 1)} % (sólo pagos en otra moneda) · ventana
          de ±{counted(settings.date_window_days, "día", "días")}
        </p>
        {view.demo_shift_days ? (
          <p className="text-[12.5px] text-ink-3">
            Las fechas del extracto de demo se movieron {counted(view.demo_shift_days, "día", "días")} para seguir el día
            en que se pagó tu lote.
          </p>
        ) : null}
        {view.payments.length === 0 ? (
          <p className="text-[12.5px] text-esc">
            Este espacio aún no pagó nada este mes: decide las facturas en el <Link href="/panel" className="underline">panel</Link> y
            vuelve a conciliar.
          </p>
        ) : null}
        {view.warnings.map((warning) => (
          <p key={warning} className="text-[12.5px] text-esc">
            {warning}
          </p>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        <Figure label="Conciliado" tally={summary.reconciled} currency={currency} unit={["movimiento", "movimientos"]} />
        <Figure label="Diferencias de cambio" tally={summary.differences} currency={currency} unit={["pago", "pagos"]} />
        <Figure label="Comisiones" tally={summary.fees} currency={currency} unit={["cargo", "cargos"]} />
        <Figure label="Sin factura" tally={summary.unexplained} currency={currency} unit={["movimiento", "movimientos"]} />
        <Figure label="Aún no en el banco" tally={summary.pending_in_bank} currency={currency} unit={["pago", "pagos"]} />
      </div>
    </section>
  );
}

function Column({
  title,
  hint,
  items,
  view,
  tone,
}: {
  title: string;
  hint: string;
  items: MovementView[];
  view: ReconciliationView;
  tone: string;
}) {
  return (
    <section aria-label={title} className="card-surface flex min-w-0 flex-col p-4">
      <h2 className="flex items-center justify-between gap-2 font-semibold">
        {title}
        <span className={cn("grid h-6 min-w-6 place-items-center rounded-full px-1.5 text-xs tabular", tone)}>
          {items.length}
        </span>
      </h2>
      <p className="text-[12.5px] text-ink-3">{hint}</p>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <MovementCard key={item.movement.id} reconciliationId={view.id} item={item} />
          ))}
        </ul>
      ) : (
        <p className="py-3 text-[13px] text-ink-3">Nada aquí.</p>
      )}
    </section>
  );
}

function PendingPayments({ view }: { view: ReconciliationView }) {
  const pending = view.payments.filter((payment) => payment.status === "pending");
  const inflows = view.movements.filter((item) => item.result.status === "inflow");
  if (!pending.length && !inflows.length) return null;
  return (
    <section aria-label="Fuera de las columnas" className="card-surface mb-4 grid gap-4 p-5 md:grid-cols-2">
      {pending.length ? (
        <div>
          <h2 className="font-semibold">Pagos que aún no aparecen en el banco</h2>
          <ul className="mt-1.5 flex flex-col gap-1.5 text-[13px]">
            {pending.map((payment) => (
              <li key={payment.invoice_id}>
                <Link href={`/panel?acta=${payment.invoice_id}`} className="font-semibold text-brand hover:underline">
                  Acta {payment.invoice_id}
                </Link>
                <span className="text-ink-2"> · {payment.supplier_name ?? ""} · {payment.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {inflows.length ? (
        <div>
          <h2 className="font-semibold">Ingresos, fuera de cuentas por pagar</h2>
          <ul className="mt-1.5 flex flex-col gap-1.5 text-[13px] text-ink-2">
            {inflows.map(({ movement }) => (
              <li key={movement.id}>
                {movement.description} · {formatMoney(movement.amount, movement.currency, { decimals: 2 })}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function Closing({ view }: { view: ReconciliationView }) {
  const api = useApi();
  const close = useClosePeriod(view.id);
  const closerId = useId();
  const [closer, setCloser] = useState("");
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const month = monthOf(view.period);
  const closed = view.period_closed;

  async function download() {
    setDownloadError(null);
    try {
      saveFile(await api.downloadEvidence(view.period), `custodio-cierre-${view.period}.zip`);
    } catch (error) {
      setDownloadError(error);
    }
  }

  let body: ReactNode;
  if (closed) {
    body = (
      <>
        <p className="flex items-center gap-2 rounded-xl bg-pay-weak px-3.5 py-3 text-[14px]">
          <Lock aria-hidden className="size-4 shrink-0 text-pay" />
          Mes cerrado por {closed.closed_by} · {formatDateTime(closed.closed_at)} · asiento #{closed.ledger_seq} (
          {shortHash(closed.ledger_hash)})
        </p>
        <Button onClick={() => void download()} className="self-start">
          <Download aria-hidden /> Descargar el paquete para el contador
        </Button>
        <p className="text-[12.5px] text-ink-3">
          ZIP con el resumen en PDF, el CSV de conciliación, todas las actas del mes y el registro con su verificación.
          El mismo estado da los mismos bytes; sólo cambia la fecha de generación del manifiesto.
        </p>
      </>
    );
  } else {
    const open = view.summary.alerts_open;
    body = (
      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          close.mutate({ period: view.period, closedBy: closer.trim() });
        }}
      >
        <p className="text-[13.5px] text-ink-2">
          {view.can_close
            ? "Todo revisado. Al cerrar, Custodio escribe el cierre en el registro y arma el paquete para el contador."
            : `Quedan ${counted(open, "salida sin revisar", "salidas sin revisar")}: cada una necesita la nota de una persona antes de cerrar.`}
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex min-w-[180px] flex-col gap-1">
            <label htmlFor={closerId} className="text-[12.5px] text-ink-2">
              Quién cierra
            </label>
            <Input id={closerId} value={closer} maxLength={120} onChange={(event) => setCloser(event.target.value)} className="h-10" />
          </div>
          <Button type="submit" disabled={!view.can_close || !closer.trim() || close.isPending}>
            <ShieldCheck aria-hidden /> Cerrar {month}
          </Button>
        </div>
      </form>
    );
  }

  return (
    <section aria-label="Cierre del mes" className="card-surface flex flex-col gap-3 p-5">
      <h2 className="font-display text-[19px] font-semibold">Cierre de {month}</h2>
      {body}
      {close.error || downloadError ? (
        <p role="alert" className="text-[13px] text-crit">
          {messageOf(close.error ?? downloadError)}
        </p>
      ) : null}
    </section>
  );
}

function Result({ view }: { view: ReconciliationView }) {
  const reconciled = view.movements.filter((item) => item.result.status === "reconciled");
  const differences = view.movements.filter((item) => DIFFERENCE_COLUMN.has(item.result.status));
  const alerts = view.movements.filter((item) => item.needs_review);
  return (
    <>
      <Overview view={view} />
      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <Column
          title="Conciliado"
          hint="El banco confirma el pago, con la razón y el nivel del emparejamiento."
          items={reconciled}
          view={view}
          tone="bg-pay-weak text-pay"
        />
        <Column
          title="Con diferencia"
          hint="Diferencias de cambio dentro de la tolerancia y comisiones del banco."
          items={differences}
          view={view}
          tone="bg-esc-weak text-ink"
        />
        <Column
          title="Alertas"
          hint="Salió dinero que ninguna factura pagada explica. Una persona revisa cada una."
          items={alerts}
          view={view}
          tone="bg-crit-weak text-crit"
        />
      </div>
      <PendingPayments view={view} />
      <Closing view={view} />
    </>
  );
}

export function ReconciliationPage() {
  const history = useReconciliations();
  const reconcile = useReconcileStatement();
  const [chosen, setChosen] = useState<string | null>(null);
  const currentId = chosen ?? history.data?.[0]?.id ?? null;
  const current = useReconciliation(currentId);

  return (
    <>
      <PageHeader
        title="Conciliación"
        subtitle="Custodio cruza el extracto del banco con lo que pagó. El modelo lee el extracto, el código empareja y cierra, una persona revisa cada alerta."
      />
      <StatementDrop
        pending={reconcile.isPending}
        onReconcile={(input) => reconcile.mutate(input, { onSuccess: (view) => setChosen(view.id) })}
      />
      {reconcile.error ? (
        <p role="alert" className="mb-4 text-crit">
          {messageOf(reconcile.error)}
        </p>
      ) : null}
      {history.error ? <ErrorState error={history.error} onRetry={() => void history.refetch()} /> : null}
      {current.error ? <ErrorState error={current.error} onRetry={() => void current.refetch()} /> : null}
      {current.data ? <Result view={current.data} /> : currentId || history.isPending ? <LoadingBlock className="h-72" /> : null}
    </>
  );
}
