"""Typed errors of the services layer. Each one carries a stable code and an honest Spanish message.

The HTTP layer maps them to status codes; the services never know about HTTP.
"""

from __future__ import annotations


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


class PolicyInvalid(ServiceError):
    code = "policy_invalid"


class InvoiceInputMissing(ServiceError):
    code = "invoice_input_missing"
    message = "Envía un archivo o el texto de la factura."


class UnsupportedMediaType(ServiceError):
    code = "unsupported_media_type"
    message = "Sólo leemos PDF, PNG, JPEG, WEBP o texto."


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
