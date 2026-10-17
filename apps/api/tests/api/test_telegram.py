from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.services.notifier import ApprovalRequest, NotificationFailed

from .conftest import WEBHOOK_SECRET, MutableClock
from .doubles import RecordingNotifier
from .helpers import Workspace, assert_ledger_valid, new_workspace, process

ANA_CHAT = "4242"


def press(client: TestClient, token: str, chat_id: str = ANA_CHAT, secret: str = WEBHOOK_SECRET) -> Any:
    update = {
        "update_id": 1,
        "callback_query": {
            "id": "callback-1",
            "from": {"id": int(chat_id)},
            "message": {"message_id": 9, "chat": {"id": int(chat_id)}},
            "data": token,
        },
    }
    return client.post("/api/v1/telegram/webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": secret})


def pending_request(client: TestClient, notifier: RecordingNotifier) -> tuple[Workspace, ApprovalRequest]:
    workspace = new_workspace(client)
    process(client, workspace)
    assert len(notifier.requests) == 1
    return workspace, notifier.requests[0]


def test_a_pending_decision_reaches_the_approver_with_two_distinct_tokens(
    client: TestClient, notifier: RecordingNotifier
) -> None:
    _, request = pending_request(client, notifier)

    assert request.chat_id == ANA_CHAT
    assert "F02" in request.text
    assert request.approve_token != request.reject_token
    assert len(request.approve_token.encode()) <= 64  # Telegram's callback_data limit


def test_the_approve_button_pays_through_the_same_service(client: TestClient, notifier: RecordingNotifier) -> None:
    workspace, request = pending_request(client, notifier)

    response = press(client, request.approve_token)

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["status"] == "paid_human"
    acta = client.get("/api/v1/decisions/F02", headers=workspace.headers).json()
    assert acta["decision"]["approval"]["channel"] == "telegram"
    assert acta["decision"]["approval"]["approver"] == "Ana Gómez"
    assert notifier.answers
    assert_ledger_valid(client, workspace)


def test_a_token_works_only_once(client: TestClient, notifier: RecordingNotifier) -> None:
    workspace, request = pending_request(client, notifier)
    press(client, request.approve_token)

    second = press(client, request.approve_token)
    sibling = press(client, request.reject_token)

    assert second.status_code == 200
    assert second.json()["handled"] is False
    assert sibling.json()["handled"] is False
    kinds = [entry["kind"] for entry in client.get("/api/v1/ledger", headers=workspace.headers).json()]
    assert kinds.count("approval") == 1


def test_the_reject_button_rejects(client: TestClient, notifier: RecordingNotifier) -> None:
    _, request = pending_request(client, notifier)

    assert press(client, request.reject_token).json()["status"] == "rejected"


def test_a_token_is_bound_to_the_chat_it_was_sent_to(client: TestClient, notifier: RecordingNotifier) -> None:
    _, request = pending_request(client, notifier)

    assert press(client, request.approve_token, chat_id="999").json()["handled"] is False
    assert press(client, request.approve_token).json()["handled"] is True


def test_a_token_expires(client: TestClient, notifier: RecordingNotifier, clock: MutableClock) -> None:
    _, request = pending_request(client, notifier)
    clock.advance(timedelta(hours=73))

    assert press(client, request.approve_token).json()["handled"] is False


def test_approving_in_the_panel_kills_the_telegram_buttons(client: TestClient, notifier: RecordingNotifier) -> None:
    workspace, request = pending_request(client, notifier)
    client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json={"approver": "Ana Gómez"})

    assert press(client, request.approve_token).json()["handled"] is False


def test_calls_without_telegram_secret_are_refused(client: TestClient, notifier: RecordingNotifier) -> None:
    _, request = pending_request(client, notifier)

    response = press(client, request.approve_token, secret="guess")

    assert response.status_code == 403
    assert press(client, request.approve_token).json()["handled"] is True


def test_updates_that_are_not_button_presses_are_acknowledged(client: TestClient) -> None:
    response = client.post(
        "/api/v1/telegram/webhook",
        json={"update_id": 2, "message": {"message_id": 1, "chat": {"id": 1}, "text": "hola"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
    )

    assert response.status_code == 200
    assert response.json()["handled"] is False


def test_a_failed_notification_never_blocks_the_decision(
    client: TestClient, notifier: RecordingNotifier, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_: ApprovalRequest) -> None:
        raise NotificationFailed("Telegram sendMessage falló (ConnectError).")

    monkeypatch.setattr(notifier, "send_approval_request", broken)
    workspace = new_workspace(client)

    result = process(client, workspace)

    assert {d["status"] for d in result["batch"]["decisions"]} == {"paid_auto", "pending_approval", "hold"}
