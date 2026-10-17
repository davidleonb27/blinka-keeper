import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { StatusPill } from "@/components/status-pill";
import type { Metrics, SimulationReport } from "@/lib/api/contracts";
import { formatPercent } from "@/lib/format";

function Delta({ label, before, after, format }: { label: string; before: number; after: number; format: (n: number) => string }) {
  const diff = after - before;
  return (
    <div className="rounded-xl border border-line px-3 py-2.5">
      <span className="block text-xs text-ink-3">{label}</span>
      <b className="text-[17px] tabular">{format(after)}</b>
      {diff ? (
        <em className="ml-1.5 text-xs text-ink-3 not-italic tabular">
          antes {format(before)}
        </em>
      ) : (
        <em className="ml-1.5 text-xs text-ink-3 not-italic">sin cambio</em>
      )}
    </div>
  );
}

const count = (n: number) => String(n);

/** What the new rules would have done to this month's invoices, before anything is applied. */
export function SimulationView({ report }: { report: SimulationReport }) {
  const { before, after } = report;
  const deltas: [string, keyof Metrics, (n: number) => string][] = [
    ["Autonomía", "autonomy_rate", (n) => formatPercent(n)],
    ["Pagadas solas", "paid_auto", count],
    ["Esperan aprobación", "pending", count],
    ["Retenidas", "hold", count],
  ];
  return (
    <section aria-label="Simulación contra el historial" className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2">
        {deltas.map(([label, key, format]) => (
          <Delta key={key} label={label} before={Number(before[key])} after={Number(after[key])} format={format} />
        ))}
      </div>
      {report.changed.length ? (
        <ul className="flex max-h-[340px] flex-col gap-2 overflow-y-auto">
          {report.changed.map((change) => (
            <li key={change.invoice_id} className="rounded-xl border border-line px-3 py-2.5">
              <Link href={`/panel?acta=${change.invoice_id}`} className="font-semibold hover:underline">
                {change.supplier_name ?? change.invoice_id}
              </Link>
              <p className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <StatusPill status={change.before} />
                <ArrowRight aria-label="pasa a" className="size-3.5 text-ink-3" />
                <StatusPill status={change.after} />
              </p>
              {change.reason ? <p className="mt-1 text-[12.5px] text-ink-3">{change.reason}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[13.5px] text-ink-3">Ninguna factura de este mes cambiaría de decisión.</p>
      )}
    </section>
  );
}
