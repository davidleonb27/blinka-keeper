/** How a person reads each field of a receipt. Mirrors custodio.receipts.signing on the API. */
export const VERDICT_LABELS: Record<string, string> = {
  pay: "Pagar",
  hold: "Retener",
  escalate: "Escalar a una persona",
  reject: "Rechazar",
};

const FIELD_LABELS: Record<string, string> = {
  format: "formato",
  key_id: "id de clave",
  workspace_id: "espacio de trabajo",
  issued_at: "fecha",
  "invoice.id": "factura",
  "invoice.number": "número de factura",
  "invoice.received_at": "fecha de recepción",
  "invoice.source": "canal de llegada",
  "invoice.document_id": "documento",
  "invoice.document_sha256": "huella del documento",
  "policy.version": "versión de la política",
  "policy.sha256": "huella de la política",
  "policy.ledger_seq": "posición de la política en el registro",
  "policy.ledger_hash": "hash de la política en el registro",
  "decision.verdict": "decisión",
  "decision.status": "estado",
  "decision.agent_verdict": "veredicto del agente",
  "decision.approved_by": "aprobado por",
  payment: "pago",
  "payment.beneficiary_id": "beneficiario",
  "payment.beneficiary_name": "beneficiario",
  "payment.account_last4": "cuenta",
  "payment.account_sha256": "cuenta",
  "payment.amount": "monto",
  "payment.currency": "moneda",
  "payment.amount_base": "monto en moneda base",
  "payment.base_currency": "moneda base",
  "payment.rail": "riel de pago",
  "payment.external_id": "id del pago",
  "ledger.seq": "posición en el registro",
  "ledger.hash": "hash en el registro",
  "ledger.kind": "tipo de asiento",
};

const READING_LABELS: Record<string, string> = {
  supplier_name: "proveedor leído",
  supplier_tax_id: "identificación fiscal leída",
  invoice_number: "número de factura leído",
  issue_date: "fecha de emisión leída",
  due_date: "vencimiento leído",
  amount: "monto leído",
  currency: "moneda leída",
  bank_name: "banco leído",
  account_number: "cuenta leída",
};

export function fieldLabel(path: string, body: Record<string, unknown>): string {
  const [section, name] = path.split(".");
  if (section === "reading" && name) return READING_LABELS[name] ?? `${name} leído`;
  if (section === "rules" && name && /^\d+$/.test(name)) {
    const rules = body.rules;
    const rule: unknown = Array.isArray(rules) ? rules[Number(name)] : undefined;
    const ruleId = rule && typeof rule === "object" ? (rule as Record<string, unknown>).rule_id : undefined;
    return typeof ruleId === "string" ? `resultado de la regla ${ruleId}` : "resultado de una regla";
  }
  return FIELD_LABELS[path] ?? path;
}

export function spanishList(items: string[]): string {
  return items.length === 1 ? items[0] : `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}
