"""Typed errors of the services layer. Each one carries a stable code and an honest Spanish message.

The HTTP layer maps them to status codes; the services never know about HTTP.
"""

from __future__ import annotations

from custodio.llm import LLMError, LLMNotConfigured


class ServiceError(Exception):
    code = "service_error"
    message = "No pudimos completar la operación."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class NotFound(ServiceError):
    code = "not_found"
    message = "No encontramos lo que buscas."


class WorkspaceNotFound(NotFound):
    code = "workspace_not_found"
    message = "No encontramos ese espacio de trabajo."


class DecisionNotFound(NotFound):
    code = "decision_not_found"
    message = "No encontramos esa decisión en este espacio."


class LedgerEntryNotFound(NotFound):
    code = "ledger_entry_not_found"
    message = "Esa posición no existe en el registro."


class InvalidApiKey(ServiceError):
    code = "invalid_api_key"
    message = "La clave de API no es válida."


class DecisionNotPending(ServiceError):
    code = "decision_not_pending"
    message = "Esta decisión ya no está esperando aprobación."


class PaymentNotRetryable(ServiceError):
    code = "payment_not_retryable"
    message = "Esta decisión no tiene un pago fallido que reintentar."


class PolicyInvalid(ServiceError):
    code = "policy_invalid"


class InvoiceInputMissing(ServiceError):
    code = "invoice_input_missing"
    message = "Envía un archivo o el texto de la factura."


class UnsupportedMediaType(ServiceError):
    code = "unsupported_media_type"
    message = "Sólo leemos PDF, PNG, JPEG, WEBP o texto."


class UnreadableSupplierFile(ServiceError):
    code = "unreadable_supplier_file"
    message = "No pudimos leer la lista de proveedores."


class UnsupportedSupplierFile(ServiceError):
    code = "unsupported_supplier_file"
    message = "Sólo importamos proveedores desde CSV, XLSX o PDF."


class PayloadTooLarge(ServiceError):
    code = "payload_too_large"
    message = "El archivo supera el máximo de 4 MB."


class RateLimited(ServiceError):
    code = "rate_limited"
    message = "Demasiadas solicitudes seguidas. Espera un minuto y vuelve a intentarlo."

    def __init__(self, retry_after_seconds: int, message: str | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class ModelUnavailable(ServiceError):
    code = "model_unavailable"
    message = "El modelo no está disponible ahora. No se tomó ninguna decisión; inténtalo de nuevo en un momento."


class ModelNotConfigured(ModelUnavailable):
    code = "model_not_configured"
    message = (
        "Esta función requiere ANTHROPIC_API_KEY y este servidor no la tiene. Lo demás (reglas, auditor, registro, "
        "firewall y lectura de texto) funciona sin ella. No se tomó ninguna decisión."
    )


def model_failure(error: LLMError) -> ModelUnavailable:
    """The service error for a model failure: a missing key is said as such, anything else as unavailable."""
    return ModelNotConfigured() if isinstance(error, LLMNotConfigured) else ModelUnavailable()


class ReadingUnavailable(ServiceError):
    """The document is stored and waits for a person; the reader could not read it now."""

    code = "reading_unavailable"
    message = "No pudimos leer la factura; queda para revisión humana."

    def __init__(self, invoice_id: str) -> None:
        super().__init__()
        self.invoice_id = invoice_id


class WorkspaceHeaderMissing(ServiceError):
    code = "workspace_header_missing"
    message = "Falta la cabecera X-Custodio-Workspace."


class SimulationNotAvailable(ServiceError):
    code = "simulation_not_available"
    message = "La simulación de 30 días sólo corre en el espacio demo, nunca con los datos de una empresa real."


class StatementInputMissing(ServiceError):
    code = "statement_input_missing"
    message = "Envía el extracto (CSV, PDF o imagen) o pide el extracto de demo."


class StatementUnreadable(ServiceError):
    code = "statement_unreadable"
    message = "No pudimos leer el extracto."


class UnsupportedStatement(ServiceError):
    code = "unsupported_statement"
    message = "Sólo leemos extractos en CSV, PDF, PNG, JPEG o WEBP."


class ReconciliationNotFound(NotFound):
    code = "reconciliation_not_found"
    message = "No encontramos esa conciliación en este espacio."


class ReconciliationConflict(ServiceError):
    """The month's state does not allow the operation: already closed, open alerts, nothing to close."""

    code = "reconciliation_conflict"


class MovementNotReviewable(ReconciliationConflict):
    code = "movement_not_reviewable"
    message = "Ese movimiento no necesita revisión o ya fue revisado."


class PeriodClosed(ReconciliationConflict):
    code = "period_closed"
    message = "Ese mes ya está cerrado: no admite más conciliaciones ni revisiones."


class PeriodNotClosed(ReconciliationConflict):
    code = "period_not_closed"
    message = "Cierra el mes para descargar su paquete de evidencia."


class CorrectionNotOffered(ServiceError):
    code = "correction_not_offered"
    message = "Esta factura no tiene una causa que el proveedor pueda corregir."


class CorrectionLinkInvalid(NotFound):
    code = "correction_link_invalid"
    message = "Este enlace de corrección no existe."


class CorrectionLinkGone(ServiceError):
    code = "correction_link_gone"
    message = "Este enlace ya no sirve. Pídale a la empresa uno nuevo si aún hace falta."


class CorrectionLinkExpired(CorrectionLinkGone):
    code = "correction_link_expired"
    message = "Este enlace venció. Pídale a la empresa uno nuevo si aún hace falta."


class CorrectionLinkUsed(CorrectionLinkGone):
    code = "correction_link_used"
    message = "Con este enlace ya se envió una corrección. Cada enlace sirve una sola vez."


class CorrectionClosed(CorrectionLinkGone):
    code = "correction_closed"
    message = "La empresa ya resolvió esta factura por otro camino; no hace falta corregirla."


class CorrectionInputInvalid(ServiceError):
    code = "correction_input_invalid"
    message = "Envíe la factura corregida (PDF o imagen) o confirme los datos que se piden."


class CorrectionOtherSupplier(CorrectionInputInvalid):
    code = "correction_other_supplier"
    message = (
        "La factura enviada no es de este proveedor, o no se pudo leer de quién es. Este enlace sólo recibe la "
        "corrección de esta factura; envíe una copia legible."
    )
