"""Runtime settings, read from environment variables. Secrets are never stored here.

API keys are read by their SDKs directly from the environment (ANTHROPIC_API_KEY, GEMINI_API_KEY);
this module only knows whether they are present.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CUSTODIO_", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = Field(
        default="sqlite:///./custodio-dev.db",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL", "CUSTODIO_DATABASE_URL"),
    )

    # Model routing. Fast: extraction structuring and narratives. Smart: policy compiler, company
    # profiler and red team attacker. Cheap: high-volume public challenge triage.
    model_fast: str = "claude-sonnet-5-5"
    model_smart: str = "claude-opus-5-5"
    model_cheap: str = "claude-haiku-5-5"
    gemini_model: str = "gemini-2.5-flash"  # lane L2 verifies the current id with models.list

    llm_daily_budget_usd: float = 25.0  # hard stop for model spend per deployment per UTC day
    public_base_url: str = ""  # e.g. https://custodio-blinka.vercel.app, used to build acta links

    telegram_bot_token_present: bool = Field(
        default_factory=lambda: bool(os.environ.get("TELEGRAM_BOT_TOKEN")), exclude=True
    )

    @property
    def anthropic_configured(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    @property
    def gemini_configured(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
