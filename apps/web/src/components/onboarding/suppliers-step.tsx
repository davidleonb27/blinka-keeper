"use client";

import { FileUp, ListChecks, TriangleAlert } from "lucide-react";
import { useId } from "react";
import { Button } from "@/components/ui/button";
import type { SupplierImport } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useImportSuppliers } from "@/lib/api/hooks";
import { formatMoney } from "@/lib/format";
import type { StepProps } from "./basic-steps";
import { focusStepHeading, StepFrame } from "./step-frame";
import { starterMoney } from "./state";

const SAMPLE_SUPPLIERS: [string, string, string, string, number][] = [
  ["Distribuidora Andina SAS", "900.112.334-5", "Bancolombia", "•••• 1204", 0.16],
  ["Nube Segura SAS", "901.554.210-3", "Davivienda", "•••• 7781", 0.045],
  ["Transportes El Cóndor", "800.443.981-2", "Banco de Bogotá", "•••• 3390", 0.07],
  ["Contadora Laura Méndez", "1.020.774.551", "Nequi", "•••• 6612", 0.11],
  ["Empaques Verdes SAS", "901.882.004-7", "BBVA", "•••• 0458", 0.6],
];

/** The columns of the template; «moneda» may be left out, and then it is the company's. */
export const SUPPLIER_TEMPLATE_HEADER = "nombre;nit;banco;cuenta;moneda;monto mensual";

/** A CSV in the same format a person would upload, scaled to the company's approval threshold. */
function sampleSupplierFile(currency: string): File {
  const threshold = starterMoney(currency).threshold;
  const rows = SAMPLE_SUPPLIERS.map(([name, taxId, bank, account, share]) =>
    [name, taxId, bank, account, currency, Math.round(threshold * share)].join(";"),
  );
  return new File([[SUPPLIER_TEMPLATE_HEADER, ...rows].join("\n")], "proveedores-ejemplo.csv", {
    type: "text/csv",
  });
}

export function SuppliersStep({ answers, update, frame }: StepProps) {
  const inputId = useId();
  const upload = useImportSuppliers();
  const load = (file: File) =>
    upload.mutate({ file, currency: answers.currency }, {
      onSuccess: (result: SupplierImport) => {
        update({ suppliers: result.beneficiaries, supplierWarnings: result.warnings });
        focusStepHeading();
      },
    });

  return (
    <StepFrame
      {...frame}
      busy={upload.isPending}
      busyLabel="Leyendo el archivo…"
      title="¿A quién le pagas?"
      helper="Sube una lista, un contrato o facturas viejas. Blinka Keeper arma la lista de beneficiarios permitidos, cada uno con su cuenta registrada."
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <label
          htmlFor={inputId}
          className="flex flex-1 cursor-pointer items-center gap-3 rounded-2xl border-2 border-dashed border-line-2 bg-surface px-4 py-4 hover:border-brand focus-within:border-brand"
        >
          <FileUp aria-hidden className="size-6 shrink-0 text-brand" />
          <span>
            <b className="block font-semibold">Subir archivo</b>
            <span className="block text-[13px] text-ink-3">CSV, Excel (XLSX) o PDF · hasta 4 MB</span>
            <span className="block text-[12.5px] text-ink-3">
              Columnas: <code>{SUPPLIER_TEMPLATE_HEADER}</code>. Sin moneda, va en {answers.currency}.
            </span>
          </span>
          <input
            id={inputId}
            type="file"
            accept=".csv,.xlsx,.pdf"
            className="sr-only"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) load(file);
            }}
          />
        </label>
        <Button type="button" variant="outline" size="lg" className="h-auto py-4" onClick={() => load(sampleSupplierFile(answers.currency))}>
          <ListChecks aria-hidden /> Usar una lista de ejemplo
        </Button>
      </div>
      {upload.error ? <p className="text-[13.5px] text-crit">{messageOf(upload.error)}</p> : null}
      {answers.supplierWarnings.map((warning) => (
        <p key={warning} className="flex gap-2 rounded-xl bg-esc-weak px-3.5 py-2.5 text-[13.5px]">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-esc" />
          {warning}
        </p>
      ))}
      {answers.suppliers.length ? (
        <section className="card-surface p-2" aria-label="Beneficiarios importados">
          <p className="px-3 pt-2 pb-1 text-[13px] text-ink-3">{answers.suppliers.length} beneficiarios permitidos</p>
          <ul className="divide-y divide-line">
            {answers.suppliers.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
                <span className="min-w-0">
                  <b className="block truncate font-semibold">{s.name}</b>
                  <span className="text-[12.5px] text-ink-3">
                    {s.bank_name} {s.account_number} · {s.tax_id}
                  </span>
                </span>
                {s.agreement ? (
                  <span className="text-right text-[13px] font-semibold whitespace-nowrap tabular">
                    {formatMoney(s.agreement.amount, s.agreement.currency)}
                    <span className="block text-xs font-normal text-ink-3">al mes</span>
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </StepFrame>
  );
}
