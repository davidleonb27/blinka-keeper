import { Check, TriangleAlert } from "lucide-react";

/** Static pictures of two screens of the demo, drawn with the app's own tokens. The figures are the demo company's. */

const TOTALS: { label: string; value: string; dot: string }[] = [
  { label: "Pagado", value: "USD 32.128", dot: "bg-pay" },
  { label: "Retenido", value: "USD 16.750", dot: "bg-hold" },
  { label: "Pendiente", value: "USD 44.787", dot: "bg-esc" },
];

const AUTONOMY_PERCENT = 63;

export function PanelMockup() {
  return (
    <figure aria-label="Ejemplo del panel" className="card-surface m-0 flex flex-col gap-4 p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Pagos indebidos</p>
          <p className="mt-1 font-mono text-[56px] leading-none font-semibold tracking-[-0.04em] tabular">0</p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-pay-weak px-2.5 py-1 text-xs font-semibold text-pay">
          <Check aria-hidden className="size-3.5" strokeWidth={2.4} /> El auditor está de acuerdo
        </span>
      </div>
      <div>
        <div className="flex items-baseline justify-between text-[13px]">
          <span className="font-medium text-ink-2">Autonomía</span>
          <span className="font-mono font-semibold tabular">{AUTONOMY_PERCENT} %</span>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-3">
          <div className="h-full rounded-full bg-brand" style={{ width: `${AUTONOMY_PERCENT}%` }} />
        </div>
      </div>
      <ul className="grid grid-cols-1 gap-2 min-[420px]:grid-cols-3">
        {TOTALS.map(({ label, value, dot }) => (
          <li key={label} className="rounded-xl border border-line bg-background px-3 py-2.5">
            <span className="flex items-center gap-1.5 text-[12px] font-medium text-ink-2">
              <span aria-hidden className={`size-1.5 rounded-full ${dot}`} /> {label}
            </span>
            <span className="mt-0.5 block font-mono text-[14px] font-semibold tabular">{value}</span>
          </li>
        ))}
      </ul>
      <figcaption className="text-[13px] text-ink-2">
        Lo que Custodio decidió este mes, con el auditor revisando cada pago antes de que salga.
      </figcaption>
    </figure>
  );
}

const STATEMENT: { bank: string; payment: string; amount: string; matched: boolean }[] = [
  { bank: "Débito 14 oct · PULSO SOFTWARE", payment: "F-004 · Pulso Software Inc.", amount: "USD 840", matched: true },
  { bank: "Débito 15 oct · KORA TRADUCC", payment: "F-001 · Kora Traducciones SAS", amount: "USD 634,15", matched: true },
  { bank: "Débito 16 oct · NUBE SEGURA", payment: "Sin pago que lo explique", amount: "USD 120", matched: false },
];

export function ReconciliationMockup() {
  return (
    <figure aria-label="Ejemplo de conciliación" className="card-surface m-0 flex flex-col gap-4 p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-3">
        <p className="headline text-[19px]">Extracto de octubre</p>
        <span className="font-mono text-[12px] text-ink-3">2 de 3 cuadran</span>
      </div>
      <ul className="overflow-hidden rounded-xl border border-line">
        {STATEMENT.map(({ bank, payment, amount, matched }) => (
          <li key={bank} className="flex items-start gap-3 px-3 py-2.5 text-[13px] [&+&]:border-t [&+&]:border-line">
            <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full ${matched ? "bg-pay-weak text-pay" : "bg-esc-weak text-esc"}`}>
              {matched ? <Check aria-hidden className="size-3" strokeWidth={2.6} /> : <TriangleAlert aria-hidden className="size-3" strokeWidth={2.4} />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-mono text-[12px] text-ink-3">{bank}</span>
              <span className={`block ${matched ? "" : "font-semibold text-esc"}`}>{payment}</span>
            </span>
            <span className="font-mono font-semibold whitespace-nowrap tabular">{amount}</span>
            <span className="sr-only">{matched ? "cuadra" : "no cuadra"}</span>
          </li>
        ))}
      </ul>
      <figcaption className="text-[13px] text-ink-2">
        Cruza el extracto del banco con cada pago y te muestra lo que no cuadra antes de cerrar el mes.
      </figcaption>
    </figure>
  );
}
