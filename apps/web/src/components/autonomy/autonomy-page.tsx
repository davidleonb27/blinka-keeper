"use client";

import { PlayCircle, ShieldAlert, ShieldCheck, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock, Meter } from "@/components/states";
import { Button } from "@/components/ui/button";
import type { SimulationResult, SupplierTrust, TrustOverview, TrustStep } from "@/lib/api/client";
import { messageOf } from "@/lib/api/errors";
import { useSimulateMonth, useTrust } from "@/lib/api/hooks";
import { formatDate, formatDateTime, formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

const CHART_HEIGHT = 180;
const STEP_LABEL: Record<TrustStep["kind"], string> = {
  trust_raised: "Confianza ganada",
  trust_revoked: "Confianza revocada",
};

function cleanPaymentsLeft(count: number): string {
  return count === 1 ? "Falta 1 pago limpio" : `Faltan ${count} pagos limpios`;
}

function nextStep(supplier: SupplierTrust, currency: string): string {
  const left = cleanPaymentsLeft(supplier.clean_needed);
  if (supplier.next_cap === null) return `${left} aprobados por una persona para ganar un tope propio.`;
  if (supplier.next_cap <= supplier.cap) return "Ya está en su techo: más pagos limpios no suben el tope.";
  return `${left} aprobado por una persona para subir a ${formatMoney(supplier.next_cap, currency)}.`;
}

function Timeline({ steps, currency }: { steps: TrustStep[]; currency: string }) {
  if (!steps.length) return null;
  return (
    <ol className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
      {steps.toReversed().map((step) => (
        <li key={step.seq} className="grid grid-cols-[18px_minmax(0,1fr)] gap-2 text-[13px]">
          {step.kind === "trust_revoked" ? (
            <ShieldAlert aria-hidden className="mt-0.5 size-4 text-crit" />
          ) : (
            <ShieldCheck aria-hidden className="mt-0.5 size-4 text-pay" />
          )}
          <div className="min-w-0">
            <p className="font-semibold">
              {STEP_LABEL[step.kind]}
              {step.rule_id ? ` · ${step.rule_id}` : ""}
              <span className="ml-2 font-normal text-ink-3">
                {formatMoney(step.cap_before, currency)} → {formatMoney(step.cap_after, currency)}
              </span>
            </p>
            <p className="break-words text-ink-2">{step.reason}</p>
            <p className="text-xs text-ink-3">
              {step.invoice_id} · {formatDateTime(step.at)} ·{" "}
              <Link href={`/registro#asiento-${step.seq}`} className="text-brand hover:underline">
                Asiento #{step.seq}
              </Link>
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function SupplierCard({ supplier, overview }: { supplier: SupplierTrust; overview: TrustOverview }) {
  const currency = overview.base_currency;
  const titleId = `confianza-${supplier.beneficiary_id}`;
  return (
    <article aria-labelledby={titleId} className="card-surface p-4" id={supplier.beneficiary_id}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id={titleId} className="font-semibold">
          {supplier.supplier_name}
        </h3>
        <span
          className={cn(
            "rounded-full px-2.5 py-0.5 text-xs font-semibold",
            supplier.supervised ? "bg-crit-weak text-crit" : supplier.has_history ? "bg-pay-weak text-pay" : "bg-surface-2 text-ink-2",
          )}
        >
          {supplier.supervised ? "En supervisión" : supplier.has_history ? "Confianza ganada" : "Tope de la política"}
        </span>
      </div>
      <p className="mt-2 flex items-baseline justify-between gap-2">
        <strong className="font-serif text-xl tabular">{formatMoney(supplier.cap, currency)}</strong>
        <span className="text-xs text-ink-3">techo {formatMoney(overview.ceiling, currency)}</span>
      </p>
      <Meter
        value={overview.ceiling ? supplier.cap / overview.ceiling : 0}
        tone={supplier.supervised ? "esc" : "pay"}
        label={`Tope de ${supplier.supplier_name} sobre el techo`}
      />
      <p className="mt-2 text-[13px] text-ink-2">{supplier.reason}</p>
      {supplier.has_history ? <p className="mt-1 text-xs text-ink-3">{nextStep(supplier, currency)}</p> : null}
      <Timeline steps={supplier.timeline} currency={currency} />
    </article>
  );
}

function AutonomyChart({ overview }: { overview: TrustOverview }) {
  const days = overview.autonomy.map((day) => ({ label: formatDate(day.day), rate: Math.round(day.rate * 100) }));
  return (
    <article className="card-surface p-5">
      <h2 className="font-semibold">Autonomía por día</h2>
      <p className="mb-3 text-[12.5px] text-ink-3">
        Parte de las facturas de cada día que Blinka Keeper pagó o retuvo sin una persona.
      </p>
      <div style={{ height: CHART_HEIGHT }} aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={days} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={11} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} tickLine={false} axisLine={false} fontSize={11} unit="%" />
            <Tooltip cursor={{ fill: "var(--surface-2)" }} formatter={(value) => [`${String(value)} %`, "Sin una persona"]} />
            <Bar dataKey="rate" fill="var(--chart-paid)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

/** Earned or about-to-earn caps first; suppliers in supervision last. */
function supplierRank(supplier: SupplierTrust): number {
  if (supplier.supervised) return 2;
  return supplier.has_history ? 0 : 1;
}

function bySupplierPromise(a: SupplierTrust, b: SupplierTrust): number {
  return supplierRank(a) - supplierRank(b) || b.cap - a.cap || a.clean_needed - b.clean_needed;
}

/** Until some supplier has earned a cap there is nothing to see but defaults and revocations. */
function anyTrustEarned(overview: TrustOverview): boolean {
  return overview.suppliers.some((supplier) => supplier.timeline.some((step) => step.kind === "trust_raised"));
}

function SimulatePrompt({ onSimulate, pending }: { onSimulate: () => void; pending: boolean }) {
  return (
    <section aria-label="Simular un mes" className="card-surface mb-4 flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
      <p className="min-w-0 flex-1 text-ink-2">
        <b className="font-semibold text-ink">Aún ningún proveedor se ganó un tope.</b> Simula un mes de facturas y mira cómo los
        pagos limpios lo suben y una señal de riesgo lo revoca.
      </p>
      <Button onClick={onSimulate} disabled={pending} className="h-12 self-start px-6 text-base sm:self-center">
        <PlayCircle aria-hidden /> {pending ? "Simulando…" : "Simular 30 días"}
      </Button>
    </section>
  );
}

function SimulationNote({ result }: { result: SimulationResult }) {
  const currency = result.trust.base_currency;
  return (
    <p role="status" className="rounded-xl bg-brand-weak px-3.5 py-3 text-[14px]">
      {result.created ? "Simulado" : "Ya estaba simulado"}: {result.days} días desde el {formatDate(result.start)}, {result.invoices}{" "}
      facturas (semilla {result.seed}). Se sumaron {formatMoney(result.inflow_base, currency)} de cobros supuestos para que la
      reserva no frenara el mes; queda dicho en el registro. Riel simulado: no se movió dinero.
    </p>
  );
}

export function AutonomyPage() {
  const trust = useTrust();
  const simulate = useSimulateMonth();
  const overview = trust.data;
  const prompt = overview !== undefined && !anyTrustEarned(overview) && !simulate.data;

  return (
    <>
      <PageHeader
        title="Autonomía"
        subtitle="Cada proveedor se gana su tope de pago automático: pagos aprobados por una persona sin incidentes lo suben; una sola señal de riesgo lo devuelve a supervisión."
      >
        {prompt ? null : (
          <Button onClick={() => simulate.mutate()} disabled={simulate.isPending}>
            <PlayCircle aria-hidden /> Simular 30 días
          </Button>
        )}
      </PageHeader>
      {prompt ? <SimulatePrompt onSimulate={() => simulate.mutate()} pending={simulate.isPending} /> : null}
      <div aria-live="polite" className="mb-4 flex flex-col gap-2">
        {simulate.data ? <SimulationNote result={simulate.data} /> : null}
        {simulate.error ? <p className="rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">{messageOf(simulate.error)}</p> : null}
      </div>
      {trust.isPending ? <LoadingBlock /> : null}
      {trust.error ? <ErrorState error={trust.error} onRetry={() => void trust.refetch()} /> : null}
      {overview ? (
        <div className="flex flex-col gap-4">
          <section aria-label="Resumen" className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
            <article className="card-surface flex flex-col gap-2 p-5">
              <h2 className="flex items-center gap-2 font-semibold">
                <TrendingUp aria-hidden className="size-4 text-brand" /> Tasa de autonomía
              </h2>
              <strong className="font-serif text-[34px] leading-none tabular">{formatPercent(overview.autonomy_rate)}</strong>
              <p className="text-[13px] text-ink-2">
                Piso {formatMoney(overview.floor, overview.base_currency)} · tope de la política{" "}
                {formatMoney(overview.policy_threshold, overview.base_currency)} · techo{" "}
                {formatMoney(overview.ceiling, overview.base_currency)}
                {overview.hard_ceiling ? " (techo duro)" : " (límite por pago)"}.
              </p>
              <p className="text-xs text-ink-3">
                Tras {overview.clean_payments_to_earn} pagos limpios el tope es la mediana aprobada; cada pago limpio más suma un
                25 %, hasta el doble. Todo sale de los asientos del registro.
              </p>
            </article>
            <AutonomyChart overview={overview} />
          </section>
          <section aria-label="Proveedores" className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {overview.suppliers.toSorted(bySupplierPromise).map((supplier) => (
              <SupplierCard key={supplier.beneficiary_id} supplier={supplier} overview={overview} />
            ))}
          </section>
        </div>
      ) : null}
    </>
  );
}
