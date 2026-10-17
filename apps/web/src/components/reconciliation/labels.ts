/** How reconciliation values read to a person. Display only: the API already decided every one of them. */
import type { MatchLevel, MovementStatus } from "@/lib/api/contracts";

const MONTHS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

export const LEVEL_LABEL: Record<MatchLevel, string> = {
  exact: "Exacto",
  amount_date: "Por monto y fecha",
  split: "Partido",
  tolerance: "Con tolerancia",
};

export const STATUS_LABEL: Record<MovementStatus, string> = {
  reconciled: "Conciliado",
  reconciled_with_difference: "Conciliado con diferencia",
  unmatched_outflow: "Salida sin factura",
  bank_fee: "Comisión bancaria",
  duplicate: "Duplicado",
  unread: "NO LEÍDO",
  inflow: "Ingreso",
};

/** "2026-10" → "octubre de 2026". */
export function monthOf(period: string): string {
  const [year, month] = period.split("-").map(Number);
  return `${MONTHS[month - 1]} de ${year}`;
}

export function counted(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
