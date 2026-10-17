"use client";

import { ArrowRight, ShieldCheck, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { Guilloche } from "@/components/brand/guilloche";
import { Chip } from "@/components/shell/page-header";
import { Meter } from "@/components/states";
import { Button } from "@/components/ui/button";
import type { WorkspaceSummary } from "@/lib/api/client";
import { formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

function ImproperPaymentsHero({ summary }: { summary: WorkspaceSummary }) {
  const improper = summary.metrics.improper_payments;
  return (
    <article className="card-surface relative flex min-h-[260px] flex-col justify-between overflow-hidden p-5 sm:p-6 lg:col-span-5">
      <Guilloche />
      <div className="relative">
        <p className="eyebrow">Pagos indebidos</p>
        <p
          className={cn(
            "my-3 text-[88px] leading-[0.95] font-semibold tracking-[-0.05em] tabular sm:text-[112px]",
            improper > 0 && "text-crit",
          )}
        >
          {improper}
        </p>
        <p className="max-w-[40ch] text-ink-2">
          Un auditor independiente recalculó uno por uno los {summary.audit.checked} pagos de este espacio antes de que
          salieran. Un solo pago indebido descalifica: este número tiene que ser cero siempre.
        </p>
      </div>
      <div className="relative mt-4 flex flex-wrap gap-2">
        {summary.audit.agrees ? (
          <Chip tone="ok">
            <ShieldCheck aria-hidden className="size-4" /> El auditor está de acuerdo
          </Chip>
        ) : (
          <Chip tone="bad">
            <ShieldAlert aria-hidden className="size-4" /> El auditor encontró diferencias
          </Chip>
        )}
      </div>
    </article>
  );
}

function Stat({ label, value, detail, children }: { label: string; value: string; detail: string; children?: React.ReactNode }) {
  return (
    <article className="card-surface flex flex-col gap-2 p-5">
      <h2 className="text-[13px] font-medium text-ink-2">{label}</h2>
      <p className="text-[32px] leading-[1.05] font-semibold tracking-[-0.02em] tabular">{value}</p>
      {children}
      <p className="text-[12.5px] text-ink-3">{detail}</p>
    </article>
  );
}

export function Overview({ summary, pendingTotal, onShowPending }: { summary: WorkspaceSummary; pendingTotal: number; onShowPending: () => void }) {
  const { metrics, base_currency: base } = summary;
  const decidedAlone = metrics.paid_auto + metrics.hold;
  const free = Math.max(0, summary.balance - summary.reserve);
  const freeMax = Math.max(1, summary.opening_balance - summary.reserve);
  return (
    <section aria-label="Resumen" className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <ImproperPaymentsHero summary={summary} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:col-span-7">
        <Stat
          label="Autonomía"
          value={formatPercent(metrics.autonomy_rate)}
          detail={`${decidedAlone} de ${metrics.total} facturas decididas sin una persona: ${metrics.paid_auto} pagadas y ${metrics.hold} retenidas.`}
        >
          <Meter value={metrics.autonomy_rate} label="Autonomía" />
        </Stat>
        <Stat
          label="Coincide con el banco de casos"
          value={formatPercent(metrics.accuracy ?? null)}
          detail="Facturas de prueba, normales y trampas, donde Custodio tomó la decisión esperada."
        >
          {metrics.accuracy != null ? <Meter value={metrics.accuracy} tone="pay" label="Coincidencia" /> : null}
        </Stat>
        <article className="card-surface flex flex-col gap-2 p-5">
          <h2 className="text-[13px] font-medium text-ink-2">Esperan tu aprobación</h2>
          <p className="text-[32px] leading-[1.05] font-semibold tracking-[-0.02em] tabular">{metrics.pending}</p>
          <p className="text-[12.5px] text-ink-3">
            {metrics.pending
              ? `${formatMoney(pendingTotal, base)} en total. Custodio no las paga sin tu sí.`
              : "Nada pendiente: todo lo demás está dentro de tus reglas."}
          </p>
          {metrics.pending ? (
            <Button variant="outline" size="sm" className="mt-auto self-start" onClick={onShowPending}>
              Revisar <ArrowRight aria-hidden />
            </Button>
          ) : (
            <Button variant="outline" size="sm" className="mt-auto self-start" asChild>
              <Link href="/reglas">Ajustar reglas</Link>
            </Button>
          )}
        </article>
        <Stat
          label="Saldo libre sobre la reserva"
          value={formatMoney(free, base)}
          detail={`Saldo ${formatMoney(summary.balance, base)} · reserva ${formatMoney(summary.reserve, base)} · cupo usado ${formatMoney(summary.spent_auto_base, base)} de ${formatMoney(summary.period_budget, base)}.`}
        >
          <Meter value={free / freeMax} label="Saldo libre sobre la reserva" />
        </Stat>
      </div>
    </section>
  );
}
