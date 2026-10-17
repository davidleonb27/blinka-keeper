"""Fixed-window counters in the database, so every serverless instance shares them.

Counters commit in their own transaction: a request that fails afterwards still counts, otherwise failing calls to a
model could be repeated for free.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import select

from custodio.db.models import RateCounterRow
from custodio.services.context import Runtime
from custodio.services.errors import RateLimited

MINUTE = 60
DAY = 24 * 60 * 60
CHALLENGE_CLOSED = "El reto público alcanzó su tope de intentos por hoy. Vuelve mañana."


def check_model_call(runtime: Runtime, *, ip: str, workspace_id: str) -> None:
    limits = runtime.limits
    _hit(runtime, f"model:ip:{_anonymous(ip)}", limits.model_calls_per_minute_per_ip, MINUTE)
    _hit(runtime, f"model:ws:{workspace_id}", limits.model_calls_per_minute_per_workspace, MINUTE)


def check_challenge_attempt(runtime: Runtime, *, ip: str) -> None:
    limits = runtime.limits
    _hit(runtime, f"challenge:ip:{_anonymous(ip)}", limits.challenge_attempts_per_minute_per_ip, MINUTE)
    _hit(runtime, "challenge:all", limits.challenge_attempts_per_day, DAY, CHALLENGE_CLOSED)


def _hit(runtime: Runtime, key: str, limit: int, window_seconds: int, message: str | None = None) -> None:
    now = runtime.clock()
    window = _window_start(now, window_seconds)
    with runtime.database.session() as session:
        counter = session.scalars(
            select(RateCounterRow).where(RateCounterRow.key == key, RateCounterRow.window_start == window)
        ).first()
        if counter is None:
            counter = RateCounterRow(key=key, window_start=window, count=0)
            session.add(counter)
        if counter.count >= limit:
            raise RateLimited(retry_after_seconds=window + window_seconds - int(now.timestamp()), message=message)
        counter.count += 1


def _window_start(now: datetime, window_seconds: int) -> int:
    seconds = int(now.timestamp())
    return seconds - seconds % window_seconds


def _anonymous(ip: str) -> str:
    """IP addresses are personal data: counters keep a short digest, never the address."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]
