import os
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.api.app import create_app
from custodio.db import Database
from custodio.reconciliation.csv_statement import read_csv_statement
from custodio.reconciliation.demo import demo_statement_csv
from custodio.reconciliation.models import Statement
from custodio.services.context import RateLimits, Runtime
from custodio.services.lanes import Lanes, production_lanes
from tests.api import doubles
from tests.api.conftest import MutableClock

GENEROUS = RateLimits(model_calls_per_minute_per_ip=1000, model_calls_per_minute_per_workspace=1000)
DEMO_DAY = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "live" in item.keywords and os.environ.get("CUSTODIO_LIVE_TESTS") != "1":
        pytest.skip("live model test: set CUSTODIO_LIVE_TESTS=1 to run it")


@dataclass
class FakeStatementReader:
    """Stands in for the Claude reading of a PDF or image: answers the demo statement, or raises `error`."""

    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, data: bytes, *, filename: str, media_type: str, default_currency: str) -> Statement:
        self.calls.append({"filename": filename, "media_type": media_type, "default_currency": default_currency})
        if self.error is not None:
            raise self.error
        statement = read_csv_statement(demo_statement_csv(), default_currency=default_currency)
        return statement.model_copy(update={"reader": "pdfplumber+claude-sonnet-5-5"})


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock(DEMO_DAY)


@pytest.fixture
def statement_reader() -> FakeStatementReader:
    return FakeStatementReader()


@pytest.fixture
def lanes(statement_reader: FakeStatementReader) -> Lanes:
    """Production wiring (real demo company, engine, auditor and ledger) without the model, as the e2e uses."""
    return replace(
        production_lanes(),
        extract_document=doubles.extract_document,
        extract_text=doubles.extract_text,
        read_statement=statement_reader,
    )


@pytest.fixture
def runtime(tmp_path: Path, lanes: Lanes, clock: MutableClock) -> Runtime:
    return Runtime(
        database=Database(f"sqlite:///{tmp_path / 'custodio.db'}"),
        lanes=lanes,
        clock=clock,
        limits=GENEROUS,
        public_base_url="https://custodio.test",
    )


@pytest.fixture
def client(runtime: Runtime) -> Iterator[TestClient]:
    with TestClient(create_app(runtime)) as test_client:
        yield test_client
