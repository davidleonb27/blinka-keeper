"use client";

import { ChevronRight, Search } from "lucide-react";
import Link from "next/link";
import { StatusPill } from "@/components/status-pill";
import { Input } from "@/components/ui/input";
import type { DecisionListItem } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { amountText, baseAmountText, mainReason, SOURCE_LABEL, supplierText } from "@/lib/presentation";
import { cn } from "@/lib/utils";
import { matchesFilter, type StatusFilter } from "./summarize";

const FILTERS: { id: StatusFilter; label: string }[] = [
  { id: "all", label: "Todas" },
  { id: "pending", label: "Esperan aprobación" },
  { id: "paid", label: "Pagadas" },
  { id: "held", label: "Retenidas" },
  { id: "rejected", label: "Rechazadas" },
];

interface DecisionListProps {
  items: DecisionListItem[];
  baseCurrency: string;
  filter: StatusFilter;
  query: string;
  onFilterChange: (filter: StatusFilter) => void;
  onQueryChange: (query: string) => void;
}

function Row({ item, baseCurrency }: { item: DecisionListItem; baseCurrency: string }) {
  const { decision } = item;
  const base = baseAmountText(decision, baseCurrency);
  return (
    <li>
      <Link
        href={{ query: { acta: decision.invoice_id } }}
        scroll={false}
        className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 rounded-xl px-3 py-3 hover:bg-surface-2 sm:grid-cols-[170px_minmax(0,1fr)_auto_20px]"
      >
        <span className="col-span-2 sm:col-span-1">
          <StatusPill status={decision.status} />
        </span>
        <span className="min-w-0">
          <b className="block truncate font-semibold">{supplierText(decision)}</b>
          <span className="block truncate text-[12.5px] text-ink-3">
            {mainReason(decision)} · {formatDate(item.received_at)} · {SOURCE_LABEL[item.source]}
          </span>
        </span>
        <span className="text-right font-semibold tabular">
          {amountText(decision)}
          {base ? <span className="block text-xs font-normal text-ink-3">{base}</span> : null}
        </span>
        <ChevronRight aria-hidden className="hidden size-4 text-ink-3 sm:block" />
      </Link>
    </li>
  );
}

export function DecisionList({ items, baseCurrency, filter, query, onFilterChange, onQueryChange }: DecisionListProps) {
  const counts = Object.fromEntries(FILTERS.map((f) => [f.id, items.filter((i) => matchesFilter(i, f.id, "")).length]));
  const visible = items.filter((item) => matchesFilter(item, filter, query)).toReversed();
  return (
    <section aria-labelledby="facturas-title" className="card-surface p-3 sm:p-4">
      <div className="flex flex-wrap items-center justify-between gap-3 px-1 pb-3">
        <div>
          <h2 id="facturas-title" className="font-semibold">Facturas</h2>
          <p className="text-[12.5px] text-ink-3">Toca una para ver su acta.</p>
        </div>
        <label className="relative w-full sm:w-64">
          <span className="sr-only">Buscar proveedor o número</span>
          <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-3" />
          <Input
            type="search"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Buscar proveedor o número"
            className="h-10 pl-9"
          />
        </label>
      </div>
      <div role="group" aria-label="Filtrar facturas" className="flex gap-1.5 overflow-x-auto px-1 pb-3 [scrollbar-width:none]">
        {FILTERS.filter((f) => f.id === "all" || counts[f.id] > 0 || f.id === filter).map((f) => (
          <button
            key={f.id}
            type="button"
            aria-pressed={filter === f.id}
            onClick={() => onFilterChange(f.id)}
            className={cn(
              "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-line-2 px-3 text-[12.5px] font-medium text-ink-2",
              filter === f.id && "border-ink bg-ink text-background",
            )}
          >
            {f.label}
            <b className="font-semibold tabular opacity-70">{counts[f.id]}</b>
          </button>
        ))}
      </div>
      {visible.length ? (
        <ul className="divide-y divide-line">
          {visible.map((item) => (
            <Row key={item.decision.invoice_id} item={item} baseCurrency={baseCurrency} />
          ))}
        </ul>
      ) : (
        <p className="px-4 py-10 text-center text-ink-3">
          <b className="mb-1 block text-[15px] text-ink">Nada con ese filtro</b>
          Prueba otro filtro o borra la búsqueda.
        </p>
      )}
    </section>
  );
}
