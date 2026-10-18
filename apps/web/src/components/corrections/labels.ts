import type { CorrectableField, CorrectionIssued, CorrectionRequest } from "@/lib/api/client";

export const REQUEST_STATUS_LABEL: Record<CorrectionRequest["status"], string> = {
  open: "Esperando corrección del proveedor",
  received: "Corrección recibida",
  closed: "Enlace anulado",
  expired: "Enlace vencido",
};

export const WHATSAPP_LABEL: Record<CorrectionIssued["whatsapp"], string> = {
  sent: "Enviado también por WhatsApp al teléfono registrado del proveedor.",
  off: "WhatsApp no está activado: copia el mensaje y envíalo tú.",
  unavailable: "El canal de WhatsApp no está desplegado: copia el mensaje y envíalo tú.",
  not_whatsapp: "La factura no llegó por WhatsApp: copia el mensaje y envíalo por el canal de siempre.",
  no_phone: "El proveedor no tiene un teléfono registrado: copia el mensaje y envíalo tú.",
  failed: "WhatsApp no pudo enviarlo: copia el mensaje y envíalo tú.",
};

export const FIELD_LABEL: Record<CorrectableField, string> = {
  amount: "Monto",
  currency: "Moneda (código, p. ej. USD o COP)",
  invoice_number: "Número de factura",
  issue_date: "Fecha de emisión (AAAA-MM-DD)",
};

/** The invoice ids whose supplier was asked for a correction and has not answered yet. */
export function waitingInvoices(requests: readonly CorrectionRequest[]): ReadonlySet<string> {
  return new Set(requests.filter((request) => request.status === "open").map((request) => request.invoice_id));
}
