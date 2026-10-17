"use client";

import { useState } from "react";
import { ActaDrawer } from "@/components/acta/acta-drawer";
import { Chip, PageHeader } from "@/components/shell/page-header";
import { ErrorState, LoadingBlock } from "@/components/states";
import { useDecisions, useWorkspaceSummary } from "@/lib/api/hooks";
import { formatDate, formatMoney } from "@/lib/format";
import { DecisionList } from "./decision-list";
import { DecisionsChart } from "./decisions-chart";
import { Overview } from "./overview";
import { decisionsByDay, statusTotals, type StatusFilter, type Total } from "./summarize";

function TotalTile({ label, total, tone, base }: { label: string; total: Total; tone: string; base: string }) {
  return (
    <div className="card-surface flex min-w-0 flex-col gap-1 p-3 sm:p-4">
      <span className="flex items-center gap-1.5 text-[12.5px] font-medium text-ink-2 sm:text-[13px]">
        <i aria-hidden className={`inline-block size-2 rounded-full ${tone}`} />
        {label}
      </span>
      <b className="truncate text-[15px] font-semibold tracking-[-0.01em] tabular sm:text-xl">{formatMoney(total.total, base)}</b>
      <span className="text-xs text-ink-3">{total.count} facturas</span>
    </div>
  );
}

export function Dashboard() {
  const summary = useWorkspaceSummary();
  const decisions = useDecisions();
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");

  const header = (
    <PageHeader title="Panel" subtitle="Lo que Custodio decidió este mes y por qué puedes confiar en eso.">
      {summary.data ? (
        <>
          <Chip tone="live">Hoy {formatDate(summary.data.today)}</Chip>
          <Chip>
            Saldo <b className="font-semibold text-ink tabular">{formatMoney(summary.data.balance, summary.data.base_currency)}</b>
          </Chip>
        </>
      ) : null}
    </PageHeader>
  );

  const error = summary.error ?? decisions.error;
  if (error) {
    return (
      <>
        {header}
        <ErrorState error={error} onRetry={() => void Promise.all([summary.refetch(), decisions.refetch()])} />
      </>
    );
  }
  if (!summary.data || !decisions.data) {
    return (
      <>
        {header}
        <div className="grid gap-4 lg:grid-cols-3">
          <LoadingBlock className="h-64 lg:col-span-1" />
          <LoadingBlock className="h-64 lg:col-span-2" />
        </div>
      </>
    );
  }

  const base = summary.data.base_currency;
  const totals = statusTotals(decisions.data);
  return (
    <>
      {header}
      <div className="flex flex-col gap-4">
        <Overview summary={summary.data} pendingTotal={totals.pending.total} onShowPending={() => setFilter("pending")} />
        <section aria-label="Pagado, retenido y pendiente" className="grid grid-cols-3 gap-2 sm:gap-4">
          <TotalTile label="Pagado" total={totals.paid} tone="bg-pay" base={base} />
          <TotalTile label="Retenido" total={totals.held} tone="bg-hold" base={base} />
          <TotalTile label="Pendiente" total={totals.pending} tone="bg-esc" base={base} />
        </section>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
          <DecisionList
            items={decisions.data}
            baseCurrency={base}
            filter={filter}
            query={query}
            onFilterChange={setFilter}
            onQueryChange={setQuery}
          />
          <div className="xl:sticky xl:top-6 xl:self-start">
            <DecisionsChart days={decisionsByDay(decisions.data)} />
          </div>
        </div>
      </div>
      <ActaDrawer />
    </>
  );
}
