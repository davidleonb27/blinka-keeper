"""What Custodio answers on WhatsApp: Spanish, short, without jargon. Approvals happen only in the app."""

from __future__ import annotations

from custodio.contracts import Decision, DecisionStatus, RuleOutcome
from custodio.engine.formatting import money
from custodio.whatsapp.errors import MediaProblem

APP_ONLY = "Las aprobaciones se hacen sólo en la app de Custodio."
UNLINKED = (
    "Hola. Este número todavía no está ligado a una empresa en Custodio. Abre el panel de Custodio, busca "
    "«Recibe facturas por WhatsApp» y envía aquí el código que aparece."
)
CODE_INVALID = "Ese código no es válido o ya se usó. Pide uno nuevo en el panel de Custodio."
CODE_EXPIRED = "Ese código venció. Pide uno nuevo en el panel de Custodio."
TOO_MANY_TRIES = "Demasiados intentos con códigos. Espera una hora y pide uno nuevo en el panel de Custodio."
UNSUPPORTED = "Por ahora sólo leemos facturas en foto, PDF o texto. Envíala en uno de esos formatos."
SEND_INVOICE = f"Envía la foto o el PDF de la factura, o pega su texto completo. {APP_ONLY}"
MEDIA_PROBLEMS = {
    MediaProblem.TOO_LARGE: "El archivo supera el máximo de 4 MB. Envía una foto más liviana o el PDF.",
    MediaProblem.MEDIA_TYPE: "Sólo leemos fotos (JPEG, PNG o WEBP) y PDF.",
}
UNREADABLE = "No pudimos leer ese archivo. Envía una foto nítida o el PDF de la factura."
UNAVAILABLE = "No pudimos recibir la factura en este momento. Reenvíala en unos minutos."
REASON_LIMIT = 140


def linked(company_name: str) -> str:
    return (
        f"Listo: este número quedó ligado a {company_name}. Envía aquí la foto o el PDF de cada factura y Custodio "
        f"la revisa con tus reglas. {APP_ONLY}"
    )


def decided(decision: Decision, invoice_number: str | None, acta_url: str) -> str:
    number = invoice_number or "la factura"
    supplier = decision.supplier_name or "un proveedor sin leer"
    amount = "un monto sin leer" if decision.amount is None else money(decision.amount, decision.currency or "")
    return f"Recibida {number} de {supplier} por {amount}. Decisión: {_verdict(decision)}. Acta: {acta_url}"


def _verdict(decision: Decision) -> str:
    if decision.status in (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN):
        failed = decision.execution is not None and decision.execution.status == "failed"
        return "Aprobada, pero el pago no salió; revísalo en la app" if failed else "Pagada"
    if decision.status is DecisionStatus.HOLD:
        return f"Retenida: {_hold_reason(decision)}"
    if decision.status is DecisionStatus.PENDING_APPROVAL:
        return "Espera tu aprobación en la app"
    return "Rechazada"


def _hold_reason(decision: Decision) -> str:
    holds = [rule.reason for rule in decision.rules if rule.outcome is RuleOutcome.HOLD]
    reason = decision.blocked_reason or (holds[0] if holds else decision.explanation)
    line = " ".join(reason.split()).rstrip(".")
    return line if len(line) <= REASON_LIMIT else line[: REASON_LIMIT - 1].rstrip() + "…"
