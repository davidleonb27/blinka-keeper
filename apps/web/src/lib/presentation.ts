/** How API values read to a person. Display only: nothing here decides anything. */
import type { Decision, DecisionStatus, InvoiceSource, RuleResult } from "./api/contracts";
import { formatMoney } from "./format";

export type Tone = "pay" | "hold" | "esc" | "muted";

export const STATUS_META: Record<DecisionStatus, { label: string; tone: Tone }> = {
  paid_auto: { label: "Pagada sola", tone: "pay" },
  paid_human: { label: "Aprobada por persona", tone: "pay" },
  hold: { label: "Retenida", tone: "hold" },
  pending_approval: { label: "Espera aprobación", tone: "esc" },
  rejected: { label: "Rechazada", tone: "muted" },
};

export function isDecisionStatus(value: unknown): value is DecisionStatus {
  return typeof value === "string" && Object.hasOwn(STATUS_META, value);
}

export const SOURCE_LABEL: Record<InvoiceSource, string> = {
  email: "Correo",
  pdf: "PDF",
  whatsapp: "WhatsApp",
  image: "Foto",
  text: "Texto",
  intent: "Otro agente",
};

export const COUNTRY_NAMES: Record<string, string> = {
  CO: "Colombia",
  US: "Estados Unidos",
  MX: "México",
  AR: "Argentina",
  BR: "Brasil",
  PE: "Perú",
  CL: "Chile",
  EC: "Ecuador",
  UY: "Uruguay",
};

export function failingRules(decision: Decision): RuleResult[] {
  return decision.rules.filter((rule) => rule.outcome === "hold" || rule.outcome === "escalate");
}

export function mainReason(decision: Decision): string {
  if (decision.blocked_reason) return "Aprobada, pero tocaría la reserva";
  const failing = failingRules(decision);
  if (failing.length === 0) return "Dentro de las reglas";
  const extra = failing.length > 1 ? ` · +${failing.length - 1}` : "";
  return `${failing[0].label}${extra}`;
}

export function amountText(decision: Decision): string {
  return decision.amount === null ? "Monto no leído" : formatMoney(decision.amount, decision.currency);
}

export function baseAmountText(decision: Decision, baseCurrency: string): string | null {
  if (decision.amount_base === null || decision.currency === baseCurrency) return null;
  return `≈ ${formatMoney(decision.amount_base, baseCurrency)}`;
}

export function supplierText(decision: Decision): string {
  return decision.supplier_name ?? "Proveedor sin nombre";
}
