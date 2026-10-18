"""The WhatsApp Business Cloud API settings. All optional: without them the channel stays hidden.

Secrets live only in the environment and in `SecretStr`, so neither a log line nor a repr ever shows them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_GRAPH_VERSION = "v23.0"


class WhatsAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WHATSAPP_", extra="ignore")

    verify_token: SecretStr | None = None
    app_secret: SecretStr | None = None
    access_token: SecretStr | None = None
    phone_number_id: str | None = None
    display_number: str | None = None  # E.164 without "+", for wa.me links
    graph_version: str = DEFAULT_GRAPH_VERSION


@dataclass(frozen=True)
class WhatsAppConfig:
    verify_token: str = field(repr=False)
    app_secret: str = field(repr=False)
    access_token: str = field(repr=False)
    phone_number_id: str
    display_number: str | None = None
    graph_version: str = DEFAULT_GRAPH_VERSION


def load_config(settings: WhatsAppSettings | None = None) -> WhatsAppConfig | None:
    """The channel's settings, or None when one of the four the webhook needs is missing."""
    settings = settings or WhatsAppSettings()
    secrets = (settings.verify_token, settings.app_secret, settings.access_token)
    if any(secret is None or not secret.get_secret_value() for secret in secrets) or not settings.phone_number_id:
        return None
    verify_token, app_secret, access_token = (secret.get_secret_value() for secret in secrets if secret is not None)
    display = (settings.display_number or "").strip().lstrip("+") or None
    return WhatsAppConfig(
        verify_token=verify_token,
        app_secret=app_secret,
        access_token=access_token,
        phone_number_id=settings.phone_number_id.strip(),
        display_number=display,
        graph_version=settings.graph_version.strip() or DEFAULT_GRAPH_VERSION,
    )
