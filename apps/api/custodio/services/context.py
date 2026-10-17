"""What every service call needs: one database session plus the process-wide runtime (lanes, clock, limits)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from custodio.config import Settings
from custodio.db import Database
from custodio.services.lanes import Lanes, production_lanes
from custodio.services.notifier import Notifier, notifier_from_environment

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class RateLimits:
    model_calls_per_minute_per_ip: int = 20
    model_calls_per_minute_per_workspace: int = 30
    challenge_attempts_per_minute_per_ip: int = 5
    challenge_attempts_per_day: int = 2000  # the public challenge's own cap, on top of llm.py's daily spend cap


@dataclass(frozen=True)
class Runtime:
    database: Database
    lanes: Lanes
    notifier: Notifier
    clock: Clock
    limits: RateLimits
    public_base_url: str
    telegram_webhook_secret: str | None

    def context(self, session: Session) -> ServiceContext:
        return ServiceContext(session=session, runtime=self)


@dataclass(frozen=True)
class ServiceContext:
    session: Session
    runtime: Runtime

    @property
    def lanes(self) -> Lanes:
        return self.runtime.lanes

    def now(self) -> datetime:
        return self.runtime.clock()


def webhook_secret_for(bot_token: str) -> str:
    """Telegram echoes this secret on every webhook call; derived from the bot token so no extra variable is needed."""
    return hashlib.sha256(f"custodio-telegram-webhook:{bot_token}".encode()).hexdigest()


def production_runtime(settings: Settings, bot_token: str | None) -> Runtime:
    return Runtime(
        database=Database(settings.database_url, serverless=settings.env == "prod"),
        lanes=production_lanes(),
        notifier=notifier_from_environment(),
        clock=utc_now,
        limits=RateLimits(),
        public_base_url=settings.public_base_url,
        telegram_webhook_secret=webhook_secret_for(bot_token) if bot_token else None,
    )
