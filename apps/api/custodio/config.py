"""Runtime settings, read from environment variables. Secrets are never stored here.

The API keys are read directly from the environment (ANTHROPIC_API_KEY by the SDK, GEMINI_API_KEY by
`extraction.gemini`); this module only knows whether they are present.
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
    # The second, independent reading R1 compares with the first. With GEMINI_API_KEY it is Gemini (another company,
    # errors that do not correlate with Claude's); without it, another Claude model with another prompt.
    model_second_reader: str = "claude-opus-5-5"
    gemini_model: str = "gemini-2.5-flash"
    second_reading_timeout_seconds: float = 90.0

    llm_daily_budget_usd: float = 25.0  # hard stop for model spend per deployment per UTC day
    public_base_url: str = ""  # e.g. https://custodio-blinka.vercel.app, used to build acta links
    payment_rail: str = "simulated"  # "stripe_test" pays through Stripe in test mode, with STRIPE_SECRET_KEY=sk_test_…
    # The yearly yield the payment calendar assumes for cash kept in the account: an assumption, not a Blinka figure.
    treasury_yield_apy: float = 4.0

    @property
    def anthropic_configured(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    @property
    def gemini_configured(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
