import { Handshake } from "lucide-react";
import type { CorrectionOverview } from "@/lib/api/client";

/** «Resueltas con el proveedor»: stopped invoices the supplier corrected and that were then paid. */
export function CorrectionsStat({ overview }: { overview: CorrectionOverview }) {
  const { requested, waiting, resolved_with_supplier: resolved, blocked_after_correction: blocked } = overview;
  return (
    <section aria-label="Resueltas con el proveedor" className="card-surface flex flex-wrap items-center gap-x-6 gap-y-2 p-4">
      <h2 className="flex items-center gap-2 text-[13px] font-medium text-ink-2">
        <Handshake aria-hidden className="size-4" /> Resueltas con el proveedor
      </h2>
      <p className="text-[24px] leading-none font-semibold tabular">
        {resolved} <span className="text-[13px] font-normal text-ink-3">de {requested} pedidas</span>
      </p>
      <p className="text-[12.5px] text-ink-3">
        {waiting} esperando corrección del proveedor · {blocked} frenadas tras corregir (cuenta distinta u otra causa
        que no se negocia). Cada corrección se decide con las mismas quince reglas.
      </p>
    </section>
  );
}
