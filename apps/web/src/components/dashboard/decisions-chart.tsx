"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipContentProps } from "recharts";
import type { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";
import { Button } from "@/components/ui/button";
import type { DayCounts } from "./summarize";

// Stack order paid → pending → held keeps adjacent fills apart for color-blind readers (validated palette).
const SERIES = [
  { key: "paid", label: "Pagada sola o aprobada", color: "var(--chart-paid)" },
  { key: "pending", label: "Espera aprobación", color: "var(--chart-pending)" },
  { key: "held", label: "Retenida o rechazada", color: "var(--chart-held)" },
] as const;

const CHART_HEIGHT = 220;
const BAR_RADIUS = 4;

function DayTooltip({ active, payload, label }: TooltipContentProps<ValueType, NameType>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="min-w-40 rounded-[10px] border border-line-2 bg-surface-3 px-2.5 py-2 text-xs shadow-card">
      <p className="mb-1 text-ink-3">{label}</p>
      {SERIES.map((series) => {
        const value = payload.find((p) => p.dataKey === series.key)?.value ?? 0;
        return (
          <p key={series.key} className="flex items-center justify-between gap-3 leading-relaxed">
            <span className="flex items-center gap-1.5 text-ink-2">
              <i className="inline-block h-0.5 w-3 rounded" style={{ background: series.color }} />
              {series.label}
            </span>
            <strong className="text-ink tabular">{value}</strong>
          </p>
        );
      })}
    </div>
  );
}

function DayTable({ days }: { days: DayCounts[] }) {
  return (
    <div className="max-h-[260px] overflow-y-auto">
      <table className="w-full text-[12.5px]">
        <caption className="sr-only">Decisiones por día</caption>
        <thead>
          <tr className="text-left text-ink-3">
            <th scope="col" className="py-1.5 font-semibold">Día</th>
            {SERIES.map((s) => (
              <th key={s.key} scope="col" className="py-1.5 text-right font-semibold">{s.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {days.map((d) => (
            <tr key={d.day} className="border-t border-line">
              <th scope="row" className="py-1.5 text-left font-medium">{d.label}</th>
              <td className="py-1.5 text-right tabular">{d.paid}</td>
              <td className="py-1.5 text-right tabular">{d.pending}</td>
              <td className="py-1.5 text-right tabular">{d.held}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DecisionsChart({ days }: { days: DayCounts[] }) {
  const [asTable, setAsTable] = useState(false);
  return (
    <article className="card-surface p-5">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold">Decisiones por día</h2>
          <p className="text-[12.5px] text-ink-3">Lo que Blinka Keeper hizo con cada factura que llegó.</p>
        </div>
        <Button variant="ghost" size="sm" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
          {asTable ? "Ver gráfica" : "Ver tabla"}
        </Button>
      </div>
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-2" aria-label="Leyenda">
        {SERIES.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5">
            <i aria-hidden className="inline-block size-2.5 rounded-[3px]" style={{ background: s.color }} />
            {s.label}
          </li>
        ))}
      </ul>
      {asTable ? (
        <DayTable days={days} />
      ) : (
        <div role="img" aria-label={`Gráfica de barras apiladas con ${days.length} días. Usa «Ver tabla» para leer las cifras.`}>
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <BarChart data={days} margin={{ top: 8, right: 4, bottom: 0, left: -24 }} barCategoryGap="28%">
              <CartesianGrid vertical={false} stroke="var(--grid)" />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "var(--ink-3)", fontSize: 11 }} minTickGap={8} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "var(--ink-3)", fontSize: 11 }} width={48} />
              <Tooltip content={DayTooltip} cursor={{ fill: "var(--grid)" }} />
              {SERIES.map((s, index) => (
                <Bar
                  key={s.key}
                  dataKey={s.key}
                  stackId="day"
                  fill={s.color}
                  stroke="var(--surface)"
                  strokeWidth={2}
                  radius={index === SERIES.length - 1 ? [BAR_RADIUS, BAR_RADIUS, 0, 0] : 0}
                  isAnimationActive={false}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </article>
  );
}
