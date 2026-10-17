"use client";

import { CalendarClock, HandCoins, Send } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import type { ScheduledItem, ScheduleView } from "@/lib/api/client";
import type { PaymentRailName } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useRunDuePayments, useSchedule } from "@/lib/api/hooks";
import { formatDate, formatMoney, formatNumber } from "@/lib/format";
import { RAIL_LABEL } from "@/lib/presentation";

const CHART_HEIGHT = 200;
const TIMING_LABEL: Record<ScheduledItem["timing"], string> = {
  discount: "Pronto pago",
  on_due: "Al vencimiento",
  overdue: "Vencida",
  no_due_date: "Sin vencimiento",
  short_of_cash: "Espera saldo",
};

function railLabel(rail: string): string {
  return rail in RAIL_LABEL ? RAIL_LABEL[rail as PaymentRailName] : rail;
}

function PaymentRow({ item, currency }: { item: ScheduledItem; currency: string }) {
  const titleId = `pago-${item.invoice_id}`;
  return (
    <li aria-labelledby={titleId} className="grid grid-cols-[64px_minmax(0,1fr)] gap-x-3 gap-y-1 px-2 py-3 sm:grid-cols-[72px_minmax(0,1fr)_auto]">
      <span className="font-semibold tabular">{item.pay_on ? formatDate(item.pay_on) : "—"}</span>
      <div className="min-w-0">
        <p id={titleId} className="font-semibold">
          {item.supplier_name}
          <Link href={`/panel?acta=${item.invoice_id}`} className="ml-2 font-mono text-[12px] font-normal text-brand hover:underline">
            {item.invoice_id}
          </Link>
        </p>
        <p className="text-[13px] break-words text-ink-2">{item.reason}</p>
        <p className="text-xs text-ink-3">
          {TIMING_LABEL[item.timing]} · vence {formatDate(item.due_date)} · Riel: {railLabel(item.rail)}
        </p>
      </div>
      <span className="col-start-2 text-right sm:col-start-auto">
        <strong className="block tabular">{formatMoney(item.amount, item.currency)}</strong>
        {item.currency !== currency ? (
          <span className="text-xs text-ink-3 tabular">≈ {formatMoney(item.amount_base, currency)}</span>
        ) : null}
      </span>
    </li>
  );
}

function BalanceChart({ schedule }: { schedule: ScheduleView }) {
  const points = schedule.balance.map((point) => ({ label: formatDate(point.day), balance: point.balance }));
  const currency = schedule.base_currency;
  const lowest = Math.min(...schedule.balance.map((point) => point.balance));
  return (
    <article className="card-surface p-5">
      <h2 className="font-semibold">Saldo proyectado contra la reserva</h2>
      <p className="mb-3 text-[12.5px] text-ink-3">
        Hoy hay {formatMoney(schedule.cash, currency)} en la cuenta; el punto más bajo de los próximos {schedule.horizon_days} días
        es {formatMoney(lowest, currency)} y la reserva es {formatMoney(schedule.reserve, currency)}.
      </p>
      <div style={{ height: CHART_HEIGHT }} aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} interval="preserveStartEnd" />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={11}
              width={56}
              domain={[Math.min(schedule.reserve, lowest) * 0.98, "auto"]}
              tickFormatter={(value: number) => formatNumber(value / 1000, 0) + " k"}
            />
            <Tooltip formatter={(value) => [formatMoney(Number(value), currency), "Saldo"]} />
            <ReferenceLine y={schedule.reserve} stroke="var(--crit)" strokeDasharray="4 4" />
            <Area dataKey="balance" type="stepAfter" stroke="var(--brand)" fill="var(--brand-weak)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function CapturedCard({ schedule }: { schedule: ScheduleView }) {
  const { captured, base_currency: currency } = schedule;
  const lines = [
    { label: "Descuentos por pronto pago", value: captured.discounts },
    { label: "Moras evitadas", value: captured.late_fees_avoided },
    { label: "Rendimiento del saldo", value: captured.treasury_yield },
  ];
  return (
    <section aria-labelledby="valor-capturado" className="card-surface flex flex-col gap-2 p-5">
      <h2 id="valor-capturado" className="flex items-center gap-2 font-semibold">
        <HandCoins aria-hidden className="size-4 text-brand" /> Valor capturado este mes
      </h2>
      <strong className="font-serif text-[30px] leading-none tabular">{formatMoney(captured.total, currency)}</strong>
      <dl className="flex flex-col gap-1 text-[13px]">
        {lines.map((line) => (
          <div key={line.label} className="flex justify-between gap-3">
            <dt className="text-ink-2">{line.label}</dt>
            <dd className="tabular">{formatMoney(line.value, currency)}</dd>
          </div>
        ))}
      </dl>
      <p className="text-xs text-ink-3">
        {captured.payments} pagos del mes. Rendimiento anual de {formatNumber(schedule.apy, Number.isInteger(schedule.apy) ? 0 : 1)} %: {schedule.apy_note}
      </p>
    </section>
  );
}

export function SchedulePage() {
  const schedule = useSchedule();
  const runDue = useRunDuePayments();
  const view = schedule.data;

  function payDue() {
    runDue.mutate(undefined, {
      onSuccess: ({ executed }) =>
        toast.success(executed.length ? `Salieron ${executed.length} pagos que vencían hoy.` : "Hoy no vence ningún pago."),
      onError: (error) => toast.error(messageOf(error)),
    });
  }

  return (
    <>
      <PageHeader
        title="Calendario"
        subtitle="Lo aprobado se paga el día que vence, no antes, salvo que un descuento por pronto pago valga más. La reserva nunca se toca."
      >
        <Button onClick={payDue} disabled={runDue.isPending}>
          <Send aria-hidden /> Pagar lo que vence hoy
        </Button>
      </PageHeader>
      {schedule.isPending ? <LoadingBlock /> : null}
      {schedule.error ? <ErrorState error={schedule.error} onRetry={() => void schedule.refetch()} /> : null}
      {view ? (
        <div className="flex flex-col gap-4">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <BalanceChart schedule={view} />
            <CapturedCard schedule={view} />
          </div>
          <section aria-labelledby="proximos-pagos" className="card-surface p-5">
            <h2 id="proximos-pagos" className="flex items-center gap-2 font-semibold">
              <CalendarClock aria-hidden className="size-4 text-brand" /> Próximos {view.horizon_days} días
            </h2>
            {view.items.length ? (
              <ol className="mt-2 divide-y divide-line">
                {view.items.map((item) => (
                  <PaymentRow key={item.invoice_id} item={item} currency={view.base_currency} />
                ))}
              </ol>
            ) : (
              <p className="mt-2 text-ink-2">No hay pagos aprobados esperando su día.</p>
            )}
          </section>
          {view.waiting.length ? (
            <section aria-labelledby="esperan-saldo" className="card-surface p-5">
              <h2 id="esperan-saldo" className="font-semibold">
                Esperan saldo
              </h2>
              <ol className="mt-2 divide-y divide-line">
                {view.waiting.map((item) => (
                  <PaymentRow key={item.invoice_id} item={item} currency={view.base_currency} />
                ))}
              </ol>
            </section>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
