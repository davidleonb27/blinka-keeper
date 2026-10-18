"""Typed errors of the WhatsApp channel, in the same shape as the services' errors."""

from __future__ import annotations

from enum import StrEnum

from custodio.services.errors import NotFound, ServiceError


class WhatsAppNotConfigured(NotFound):
    code = "whatsapp_not_configured"
    message = "El canal de WhatsApp no está configurado en este servidor."


class WebhookForbidden(ServiceError):
    code = "whatsapp_verify_token_mismatch"
    message = "El token de verificación no coincide."


class WebhookSignatureInvalid(ServiceError):
    code = "whatsapp_signature_invalid"
    message = "La firma X-Hub-Signature-256 no es válida."


class WebhookPayloadInvalid(ServiceError):
    code = "whatsapp_payload_invalid"
    message = "El cuerpo del webhook no tiene la forma que envía WhatsApp."


class PhoneNotLinked(ServiceError):
    code = "whatsapp_phone_not_linked"
    message = "Ese teléfono no está ligado a este espacio de trabajo."


class MediaProblem(StrEnum):
    TOO_LARGE = "too_large"
    MEDIA_TYPE = "media_type"


class MediaRejected(Exception):
    """The file in a message is one Custodio does not read: too large or of a type it does not accept."""

    def __init__(self, problem: MediaProblem) -> None:
        super().__init__(problem.value)
        self.problem = problem


class GraphUnavailable(Exception):
    """The Graph API did not answer as expected. The message never carries a token or a response body."""


class LinkCodeInvalid(ServiceError):
    code = "whatsapp_link_code_invalid"
    message = "Ese código no es válido o ya se usó."


class LinkCodeExpired(ServiceError):
    code = "whatsapp_link_code_expired"
    message = "Ese código venció."
