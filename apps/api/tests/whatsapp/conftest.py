from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from custodio.api.app import create_app
from custodio.services.context import Runtime
from custodio.whatsapp.channel import WhatsAppChannel
from custodio.whatsapp.config import WhatsAppConfig
from tests.api.conftest import auditor, clock, database, lanes, limits  # noqa: F401 - shared fixtures
from tests.api.conftest import runtime as plain_runtime  # noqa: F401

from .doubles import ACCESS_TOKEN, APP_SECRET, DISPLAY_NUMBER, PHONE_NUMBER_ID, VERIFY_TOKEN, FakeGraph

CONFIG = WhatsAppConfig(
    verify_token=VERIFY_TOKEN,
    app_secret=APP_SECRET,
    access_token=ACCESS_TOKEN,
    phone_number_id=PHONE_NUMBER_ID,
    display_number=DISPLAY_NUMBER,
)


@pytest.fixture
def graph() -> FakeGraph:
    return FakeGraph()


@pytest.fixture
def channel(graph: FakeGraph) -> WhatsAppChannel:
    return WhatsAppChannel(config=CONFIG, graph=graph)


@pytest.fixture
def runtime(plain_runtime: Runtime, channel: WhatsAppChannel) -> Runtime:  # noqa: F811
    return replace(plain_runtime, whatsapp=channel)


@pytest.fixture
def client(runtime: Runtime) -> Iterator[TestClient]:
    with TestClient(create_app(runtime)) as test_client:
        yield test_client
