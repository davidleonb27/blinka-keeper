import json
from datetime import timedelta

from fastapi.testclient import TestClient

from custodio.whatsapp.graph import Media
from custodio.whatsapp.signature import sign
from tests.api.conftest import MutableClock
from tests.api.doubles import invoice_text
from tests.api.helpers import new_workspace

from .doubles import (
    APP_SECRET,
    SENDER,
    VERIFY_TOKEN,
    WEBHOOK,
    FakeGraph,
    deliver,
    fixture,
    link_phone,
    message,
    text,
)

SUBSCRIBE = {"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "1158201444"}


def test_meta_verification_gets_the_challenge_back_as_plain_text(client: TestClient) -> None:
    response = client.get(WEBHOOK, params=SUBSCRIBE)

    assert response.status_code == 200
    assert response.text == "1158201444"
    assert response.headers["content-type"].startswith("text/plain")


def test_a_wrong_verify_token_or_mode_is_forbidden(client: TestClient) -> None:
    assert client.get(WEBHOOK, params={**SUBSCRIBE, "hub.verify_token": "guess"}).status_code == 403
    assert client.get(WEBHOOK, params={**SUBSCRIBE, "hub.mode": "unsubscribe"}).status_code == 403
    assert client.get(WEBHOOK).status_code == 403


def test_a_delivery_without_a_valid_signature_is_refused_unread(client: TestClient, graph: FakeGraph) -> None:
    body = json.dumps(text("Hola")).encode()

    unsigned = client.post(WEBHOOK, content=body, headers={"Content-Type": "application/json"})
    forged = deliver(client, text("Hola"), secret="not-the-app-secret")

    assert unsigned.status_code == 401
    assert forged.status_code == 401
    assert forged.json()["code"] == "whatsapp_signature_invalid"
    assert graph.sent == []


def test_a_body_over_the_webhook_limit_is_refused(client: TestClient) -> None:
    body = b"{" + b" " * (256 * 1024) + b"}"

    response = client.post(WEBHOOK, content=body, headers={"X-Hub-Signature-256": sign(body, APP_SECRET)})

    assert response.status_code == 413


def test_status_updates_are_answered_and_ignored(client: TestClient, graph: FakeGraph) -> None:
    response = deliver(client, fixture("status_update"))

    assert response.status_code == 200
    assert response.json() == {"messages": 0}
    assert graph.sent == []


def test_an_unlinked_phone_gets_instructions_and_nothing_is_read(client: TestClient, graph: FakeGraph) -> None:
    deliver(client, message("image_message"))

    [reply] = graph.replies_to(SENDER)
    assert "no está ligado" in reply
    assert graph.fetched == []


def test_the_code_from_the_panel_links_the_phone_to_that_workspace(client: TestClient, graph: FakeGraph) -> None:
    workspace = new_workspace(client)

    link_phone(client, workspace)

    [reply] = graph.replies_to(SENDER)
    assert reply.startswith("Listo: este número quedó ligado a")
    phones = client.get("/api/v1/whatsapp/link", headers=workspace.headers).json()["phones"]
    assert [phone["masked"] for phone in phones] == ["+57 ••• 4567"]


def test_a_code_works_once(client: TestClient, graph: FakeGraph) -> None:
    workspace = new_workspace(client)
    code = client.post("/api/v1/whatsapp/link-codes", headers=workspace.headers).json()["message"]

    deliver(client, text(code, sender=SENDER))
    deliver(client, text(code, sender="573009998877"))

    assert "no es válido o ya se usó" in graph.replies_to("573009998877")[0]
    assert len(client.get("/api/v1/whatsapp/link", headers=workspace.headers).json()["phones"]) == 1


def test_an_expired_code_does_not_link(client: TestClient, graph: FakeGraph, clock: MutableClock) -> None:
    workspace = new_workspace(client)
    code = client.post("/api/v1/whatsapp/link-codes", headers=workspace.headers).json()["message"]
    clock.advance(timedelta(minutes=11))

    deliver(client, text(code))

    assert "venció" in graph.replies_to(SENDER)[0]
    assert client.get("/api/v1/whatsapp/link", headers=workspace.headers).json()["phones"] == []


def test_guessing_codes_runs_out_of_tries(client: TestClient, graph: FakeGraph) -> None:
    for guess in ("AAAAAA", "BBBBBB", "CCCCCC", "DDDDDD", "EEEEEE", "FFFFFF"):
        deliver(client, text(f"Vincular {guess}"))

    replies = graph.replies_to(SENDER)
    assert all("no es válido" in reply for reply in replies[:5])
    assert "Demasiados intentos" in replies[5]


def test_a_retried_delivery_is_read_once(client: TestClient, graph: FakeGraph) -> None:
    workspace = new_workspace(client)
    link_phone(client, workspace)
    graph.files["1003383421387256"] = Media(data=invoice_text(number="FV-7001").encode(), media_type="image/jpeg")
    photo = message("image_message")

    first = deliver(client, photo)
    retry = deliver(client, photo)

    assert first.status_code == retry.status_code == 200
    assert graph.fetched == ["1003383421387256"]
    items = client.get("/api/v1/decisions", headers=workspace.headers).json()
    assert [item["invoice_number"] for item in items if item["source"] == "whatsapp"] == ["FV-7001"]
    assert len(graph.replies_to(SENDER)) == 2  # the link confirmation and one answer for the photo
