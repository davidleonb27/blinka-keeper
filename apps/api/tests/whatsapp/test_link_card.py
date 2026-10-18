from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from custodio.api.app import create_app
from custodio.services.context import Runtime
from tests.api.helpers import new_workspace

from .doubles import DISPLAY_NUMBER, WEBHOOK, deliver, text


@pytest.fixture
def unconfigured(plain_runtime: Runtime) -> Iterator[TestClient]:
    with TestClient(create_app(plain_runtime)) as client:
        yield client


def test_a_code_comes_with_a_wa_me_link_that_carries_it(client: TestClient) -> None:
    workspace = new_workspace(client)

    created = client.post("/api/v1/whatsapp/link-codes", headers=workspace.headers).json()

    link = urlparse(created["link_url"])
    assert (link.netloc, link.path) == ("wa.me", f"/{DISPLAY_NUMBER}")
    assert parse_qs(link.query)["text"] == [f"Vincular {created['code']}"]
    assert len(created["code"]) == 6


def test_the_card_is_on_and_lists_no_phone_before_linking(client: TestClient) -> None:
    workspace = new_workspace(client)

    card = client.get("/api/v1/whatsapp/link", headers=workspace.headers).json()

    assert card == {"enabled": True, "display_number": DISPLAY_NUMBER, "phones": [], "last_received_at": None}


def test_without_settings_the_channel_is_hidden_and_the_webhook_is_not_there(unconfigured: TestClient) -> None:
    workspace = new_workspace(unconfigured)

    card = unconfigured.get("/api/v1/whatsapp/link", headers=workspace.headers).json()
    code = unconfigured.post("/api/v1/whatsapp/link-codes", headers=workspace.headers)
    verify = unconfigured.get(WEBHOOK, params={"hub.mode": "subscribe"})
    delivery = deliver(unconfigured, text("Hola"))

    assert card["enabled"] is False
    assert code.status_code == verify.status_code == delivery.status_code == 404
    assert delivery.json()["code"] == "whatsapp_not_configured"
