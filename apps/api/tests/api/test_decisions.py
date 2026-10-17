import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi.testclient import TestClient

from custodio.contracts import BatchResult
from custodio.services.lanes import Lanes

from .doubles import invoice_text
from .helpers import assert_ledger_valid, new_workspace, process, upload_text

APPROVER = {"approver": "Ana Gómez", "note": "Revisado con el contrato"}
WAIT_SECONDS = 5


def test_the_list_returns_every_decision_in_arrival_order(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.get("/api/v1/decisions", headers=workspace.headers)

    assert response.status_code == 200
    assert [item["decision"]["invoice_id"] for item in response.json()] == ["F01", "F02", "F03"]


def test_each_listed_decision_says_when_and_through_which_channel_its_invoice_arrived(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    first = client.get("/api/v1/decisions", headers=workspace.headers).json()[0]

    assert set(first) == {"decision", "received_at", "source", "invoice_number"}
    assert first["received_at"].startswith("2026-10-10T09:00:00")
    assert first["source"] == "text"


def test_each_listed_decision_carries_the_invoice_number_it_read(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    items = client.get("/api/v1/decisions", headers=workspace.headers).json()

    assert all(item["invoice_number"] for item in items)


def test_the_list_filters_by_status(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.get("/api/v1/decisions", headers=workspace.headers, params={"status": "hold"})

    assert [item["decision"]["invoice_id"] for item in response.json()] == ["F03"]


def test_the_acta_brings_the_decision_the_reading_and_its_ledger_entries(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.get("/api/v1/decisions/F03", headers=workspace.headers)

    assert response.status_code == 200
    acta = response.json()
    assert acta["decision"]["status"] == "hold"
    assert len(acta["decision"]["rules"]) == 15
    assert acta["invoice"]["extraction"]["account_number"]["value"] == "999000111"
    assert [entry["kind"] for entry in acta["ledger"]] == ["invoice_received", "decision"]


def test_an_undecided_invoice_has_no_acta(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = client.get("/api/v1/decisions/F01", headers=workspace.headers)

    assert response.status_code == 404
    assert response.json()["code"] == "decision_not_found"


def test_a_person_approves_a_pending_decision_and_it_is_paid(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json=APPROVER)
    summary = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    assert response.status_code == 200
    decision = response.json()
    assert decision["status"] == "paid_human"
    assert decision["approval"]["approver"] == "Ana Gómez"
    assert decision["approval"]["channel"] == "web"
    assert summary["balance"] == 100000.0 - 1200.0 - 7000.0
    assert_ledger_valid(client, workspace)


def test_a_person_rejects_a_pending_decision(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.post("/api/v1/decisions/F02/reject", headers=workspace.headers, json=APPROVER)

    assert response.json()["status"] == "rejected"
    assert_ledger_valid(client, workspace)


def test_a_decision_is_approved_only_once(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json=APPROVER)

    again = client.post("/api/v1/decisions/F02/reject", headers=workspace.headers, json=APPROVER)

    assert again.status_code == 409
    assert again.json()["code"] == "decision_not_pending"


def test_two_simultaneous_approvals_pay_only_once(client: TestClient, lanes: Lanes) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    honest, inside, release = lanes.decide_all, threading.Event(), threading.Event()

    def held_open(*args: Any, **kwargs: Any) -> BatchResult:
        if not inside.is_set():  # the first approval stays open in its transaction until released
            inside.set()
            release.wait(WAIT_SECONDS)
        return honest(*args, **kwargs)

    object.__setattr__(lanes, "decide_all", held_open)

    def approve() -> int:
        return client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json=APPROVER).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(approve)
        inside.wait(WAIT_SECONDS)
        second = pool.submit(approve)
        time.sleep(0.3)  # the second approval reaches the decision while the first still holds it
        release.set()
        codes = sorted([first.result(), second.result()])

    ledger = client.get("/api/v1/ledger", headers=workspace.headers).json()
    assert codes == [200, 409]
    assert [e["subject_id"] for e in ledger if e["kind"] == "payment"].count("F02") == 1
    assert_ledger_valid(client, workspace)


def test_a_hold_cannot_be_approved_into_a_payment(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.post("/api/v1/decisions/F03/approve", headers=workspace.headers, json=APPROVER)

    assert response.status_code == 409


def test_an_approval_is_checked_against_the_balance_at_approval_time(client: TestClient) -> None:
    workspace = new_workspace(client)
    policy = client.get("/api/v1/policy", headers=workspace.headers).json()
    client.put("/api/v1/policy", headers=workspace.headers, json={**policy, "reserve": 91000})
    process(client, workspace)  # F01 paid: 98.800 left; F02 (7.000) still fits above the reserve
    upload_text(client, workspace, invoice_text(number="FV-600", amount="1000.00"))
    process(client, workspace)  # 97.800 left: F02 no longer fits

    decision = client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json=APPROVER).json()

    assert decision["status"] == "hold"
    assert decision["blocked_reason"]
    assert client.get("/api/v1/workspaces/current", headers=workspace.headers).json()["balance"] == 97800.0
    assert_ledger_valid(client, workspace)


def test_the_approver_name_is_required(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json={"approver": " "})

    assert response.status_code == 422


def test_a_workspace_cannot_see_or_approve_another_workspace_decisions(client: TestClient) -> None:
    owner, intruder = new_workspace(client), new_workspace(client, mode="blank")
    process(client, owner)
    upload_text(client, intruder, invoice_text(number="FV-777"))

    seen = client.get("/api/v1/decisions/F02", headers=intruder.headers)
    approved = client.post("/api/v1/decisions/F02/approve", headers=intruder.headers, json=APPROVER)
    listed = client.get("/api/v1/decisions", headers=intruder.headers).json()

    assert seen.status_code == 404
    assert approved.status_code == 404
    assert listed == []
    assert client.get("/api/v1/decisions/F02", headers=owner.headers).json()["decision"]["status"] == (
        "pending_approval"
    )


def test_the_narrative_explains_a_decision_in_plain_words(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.get("/api/v1/decisions/F03/narrative", headers=workspace.headers)

    assert response.status_code == 200
    assert response.json()["narrative"].startswith("En palabras simples")


def test_approvals_are_web_only_and_there_is_no_telegram_route(client: TestClient) -> None:
    response = client.post("/api/v1/telegram/webhook", json={"update_id": 1})

    assert response.status_code == 404
    assert not any("telegram" in path for path in client.get("/api/v1/openapi.json").json()["paths"])
