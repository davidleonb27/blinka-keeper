import { BadgeCheck } from "lucide-react";
import type { ExtractedFieldName, ExtractedInvoice } from "@/lib/api/contracts";
import { formatDate, formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

const FIELD_LABELS: Record<ExtractedFieldName, string> = {
  supplier_name: "Proveedor",
  supplier_tax_id: "Identificación fiscal",
  invoice_number: "Número",
  issue_date: "Fecha de emisión",
  due_date: "Vence",
  amount: "Monto",
  currency: "Moneda",
  bank_name: "Banco",
  account_number: "Cuenta",
  description: "Concepto",
};

// R1 reads these four; they are shown even when missing so the gap is visible.
const ALWAYS_SHOWN = new Set<ExtractedFieldName>(["supplier_name", "amount", "currency", "account_number"]);

function displayValue(name: ExtractedFieldName, extraction: ExtractedInvoice): string | null {
  const value = extraction[name].value;
  if (value === null) return null;
  if (name === "amount") return formatMoney(Number(value), extraction.currency.value);
  if (name === "issue_date" || name === "due_date") return formatDate(value);
  return value;
}

export function ExtractedFields({
  extraction,
  minConfidence,
  onFocusField,
}: {
  extraction: ExtractedInvoice;
  minConfidence: number;
  onFocusField: (field: ExtractedFieldName | null) => void;
}) {
  const fields = (Object.keys(FIELD_LABELS) as ExtractedFieldName[]).filter(
    (name) => ALWAYS_SHOWN.has(name) || extraction[name].value !== null,
  );
  return (
    <ul aria-label="Lo que leyó" className="grid grid-cols-2 gap-2">
      {fields.map((name) => {
        const field = extraction[name];
        const low = field.confidence < minConfidence;
        return (
          <li
            key={name}
            tabIndex={field.evidence ? 0 : undefined}
            onMouseEnter={() => onFocusField(name)}
            onMouseLeave={() => onFocusField(null)}
            onFocus={() => onFocusField(name)}
            onBlur={() => onFocusField(null)}
            className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-2.5 gap-y-0.5 rounded-[10px] border border-line px-3 py-2 hover:border-brand focus-visible:border-brand"
          >
            <span className="text-[11.5px] text-ink-3">{FIELD_LABELS[name]}</span>
            <span className="flex items-center gap-1 text-right text-[11.5px] text-ink-3 tabular">
              {field.verified ? <BadgeCheck aria-label="Cita verificada" className="size-3.5 text-pay" /> : null}
              {formatPercent(field.confidence)}
            </span>
            <span className="col-span-2 font-semibold break-words">
              {displayValue(name, extraction) ?? <em className="font-medium text-crit not-italic">No se leyó</em>}
            </span>
            <span aria-hidden className="col-span-2 mt-1 h-[3px] overflow-hidden rounded-full bg-surface-3">
              <i
                className={cn("block h-full", low ? "bg-esc" : "bg-brand")}
                style={{ width: `${Math.round(field.confidence * 100)}%` }}
              />
            </span>
          </li>
        );
      })}
    </ul>
  );
}
