"""What every service call needs: one database session plus the process-wide runtime (lanes, clock, limits)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from custodio.config import Settings
from custodio.db import Database
from custodio.payments import PaymentRail, RailChoice, choose_rail, simulated_choice
from custodio.services.lanes import Lanes, production_lanes

if TYPE_CHECKING:
    from custodio.whatsapp.channel import WhatsAppChannel

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class RateLimits:
    model_calls_per_minute_per_ip: int = 20
    model_calls_per_minute_per_workspace: int = 30
    challenge_attempts_per_minute_per_ip: int = 30
    challenge_attempts_per_day: int = 2000  # the public challenge's own cap, on top of llm.py's daily spend cap
    test_transfers_per_workspace: int = 40  # Stripe test-mode transfers: keep the shared test account tidy
    test_transfers_per_day: int = 2000  # per UTC day, across the whole deployment
    payment_attempts_per_invoice: int = 5  # each retry of a failed payment calls Stripe; a click loop must not
    whatsapp_messages_per_minute_per_phone: int = 10  # each message may call the model; a loop must not
    whatsapp_link_attempts_per_hour_per_phone: int = 5  # a wrong code costs a try: guessing one is out of reach


@dataclass(frozen=True)
class Runtime:
    database: Database
    lanes: Lanes
    clock: Clock
    limits: RateLimits
    public_base_url: str
    payment_rail: RailChoice = field(default_factory=simulated_choice)
    treasury_yield_apy: Decimal = Decimal("4.0")  # percent a year; the payment calendar's stated assumption
    whatsapp: WhatsAppChannel | None = None  # None: the WhatsApp channel is not configured and stays hidden

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

    def payment_rail(self) -> PaymentRail:
        return self.runtime.payment_rail.build(self.session, self.runtime.clock)


def production_runtime(settings: Settings) -> Runtime:
    from custodio.whatsapp.channel import load_channel  # here: the channel's package builds on the services

    return Runtime(
        database=Database(settings.database_url, serverless=settings.env == "prod"),
        lanes=production_lanes(),
        clock=utc_now,
        limits=RateLimits(),
        public_base_url=settings.public_base_url,
        payment_rail=choose_rail(settings.payment_rail, os.environ.get("STRIPE_SECRET_KEY")),
        treasury_yield_apy=Decimal(str(settings.treasury_yield_apy)),
        whatsapp=load_channel(),
    )
