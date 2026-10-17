from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from custodio.api.app import create_app
from custodio.db import Database
from custodio.services.context import RateLimits, Runtime
from custodio.services.lanes import Lanes

from .doubles import FakeAuditor, RecordingNotifier, fake_lanes

WEBHOOK_SECRET = "webhook-secret-for-tests"
GENEROUS = RateLimits(
    model_calls_per_minute_per_ip=1000,
    model_calls_per_minute_per_workspace=1000,
    challenge_attempts_per_minute_per_ip=1000,
    challenge_attempts_per_day=1000,
)


@dataclass
class MutableClock:
    now: datetime

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock(datetime(2026, 10, 17, 15, 0, tzinfo=UTC))


@pytest.fixture
def auditor() -> FakeAuditor:
    return FakeAuditor()


@pytest.fixture
def lanes(auditor: FakeAuditor) -> Lanes:
    return fake_lanes(auditor)


@pytest.fixture
def notifier() -> RecordingNotifier:
    return RecordingNotifier()


@pytest.fixture
def limits() -> RateLimits:
    return GENEROUS


@pytest.fixture
def database(tmp_path: Path) -> Database:
    return Database(f"sqlite:///{tmp_path / 'custodio.db'}")


@pytest.fixture
def runtime(
    database: Database, lanes: Lanes, notifier: RecordingNotifier, clock: MutableClock, limits: RateLimits
) -> Runtime:
    return Runtime(
        database=database,
        lanes=lanes,
        notifier=notifier,
        clock=clock,
        limits=limits,
        public_base_url="https://custodio.test",
        telegram_webhook_secret=WEBHOOK_SECRET,
    )


@pytest.fixture
def client(runtime: Runtime) -> Iterator[TestClient]:
    with TestClient(create_app(runtime)) as test_client:
        yield test_client
