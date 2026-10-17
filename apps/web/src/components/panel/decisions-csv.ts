import type { DecisionListItem } from "@/lib/api/client";
import { failingRules, STATUS_META } from "@/lib/presentation";

const COLUMNS = ["proveedor", "numero", "monto", "moneda", "estado", "regla_decisiva", "fecha", "id_transferencia"];
const WITHIN_RULES = "Dentro de las reglas";
const NEEDS_QUOTES = /[",\r\n]/;

function cell(value: string | number | null | undefined): string {
  const text = value === null || value === undefined ? "" : String(value);
  return NEEDS_QUOTES.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function decisiveRule(item: DecisionListItem): string {
  const [first] = failingRules(item.decision);
  return first ? `${first.rule_id} ${first.label}` : (item.decision.blocked_reason ?? WITHIN_RULES);
}

function rowOf(item: DecisionListItem): (string | number | null | undefined)[] {
  const { decision } = item;
  return [
    decision.supplier_name,
    item.invoice_number,
    decision.amount,
    decision.currency,
    STATUS_META[decision.status].label,
    decisiveRule(item),
    item.received_at.slice(0, 10),
    decision.execution?.external_id,
  ];
}

/** The panel's list as CSV (RFC 4180), with plain numbers and ISO dates so a spreadsheet reads them as such. */
export function decisionsCsv(items: DecisionListItem[]): string {
  return [COLUMNS, ...items.map(rowOf)].map((row) => row.map(cell).join(",")).join("\r\n") + "\r\n";
}
