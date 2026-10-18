"""Signed receipts through the API: issued for every decision, checkable by anyone, required by the rail's guard."""

from __future__ import annotations

import base64
import copy
import hashlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.receipts import ReceiptPublicKey, verify_receipt
from custodio.services import policy_service, receipt_service, records
from custodio.services.context import Runtime
from custodio.services.errors import ReceiptUnavailable

from .doubles import invoice_text
from .helpers import assert_ledger_valid, new_workspace, process, upload_text

API = "/api/v1"


def public_key(client: TestClient) -> ReceiptPublicKey:
    view = client.get(f"{API}/.well-known/custodio-receipt-key").json()
    return ReceiptPublicKey(base64.b64decode(view["public_key"]))


def receipt(client: TestClient, workspace: Any, invoice_id: str) -> dict[str, Any]:
    response = client.get(f"{API}/decisions/{invoice_id}/receipt", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_the_public_key_is_served_with_its_id_without_a_workspace(client: TestClient) -> None:
    response = client.get(f"{API}/.well-known/custodio-receipt-key")

    assert response.status_code == 200
    view = response.json()
    assert view["algorithm"] == "Ed25519"
    assert view["key_id"].startswith("cust-")
    assert view["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")


def test_every_decision_has_a_receipt_a_third_party_verifies_with_the_public_key(client: TestClient) -> None:
    workspace = new_workspace(client)
    batch = process(client, workspace)
    key = public_key(client)

    for decision in batch["batch"]["decisions"]:
        signed = receipt(client, workspace, decision["invoice_id"])
        check = verify_receipt(signed, key)
        assert check.valid, check.message
        assert signed["body"]["invoice"]["id"] == decision["invoice_id"]
        assert signed["body"]["decision"]["status"] == decision["status"]


def test_a_paid_receipt_names_what_was_paid_to_whom_and_where_it_sits_in_the_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    body = receipt(client, workspace, "F01")["body"]
    ledger = client.get(f"{API}/ledger", headers=workspace.headers).json()

    assert body["decision"]["verdict"] == "pay"
    assert body["payment"]["amount_base"] and body["payment"]["account_sha256"]
    assert body["payment"]["rail"] == "simulated"
    entry = next(e for e in ledger if e["seq"] == body["ledger"]["seq"])
    assert entry["hash"] == body["ledger"]["hash"]
    assert entry["kind"] == "decision" and entry["subject_id"] == "F01"
    assert len(body["rules"]) == 15
    assert body["policy"]["sha256"] and body["policy"]["ledger_seq"] < body["ledger"]["seq"]
    assert_ledger_valid(client, workspace)


def test_the_receipt_fingerprints_the_document_that_was_read(client: TestClient) -> None:
    workspace = new_workspace(client)
    text = invoice_text(number="FV-900")
    invoice = upload_text(client, workspace, text)
    process(client, workspace)

    body = receipt(client, workspace, invoice["id"])["body"]

    assert body["invoice"]["document_id"] == invoice["document_id"]
    assert body["invoice"]["document_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert body["reading"]["invoice_number"] == {"value": "FV-900", "verified": True}


def test_a_held_decision_gets_a_receipt_with_no_payment(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    body = receipt(client, workspace, "F03")["body"]

    assert body["decision"]["verdict"] == "hold"
    assert body["payment"] is None


def test_the_same_decision_always_gives_the_same_receipt(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    assert receipt(client, workspace, "F01") == receipt(client, workspace, "F01")


def test_a_receipt_is_only_served_to_its_workspace(client: TestClient) -> None:
    owner, stranger = new_workspace(client), new_workspace(client)
    process(client, owner)

    response = client.get(f"{API}/decisions/F01/receipt", headers=stranger.headers)

    assert response.status_code == 404


def test_an_undecided_invoice_has_no_receipt(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = client.get(f"{API}/decisions/F01/receipt", headers=workspace.headers)

    assert response.status_code == 404


def test_the_server_check_says_valid_and_names_an_altered_amount(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    signed = receipt(client, workspace, "F01")
    tampered = copy.deepcopy(signed)
    tampered["body"]["payment"]["amount"] = "999999"

    valid = client.post(f"{API}/receipts/verify", json=signed).json()
    invalid = client.post(f"{API}/receipts/verify", json=tampered).json()

    assert valid["valid"] is True and valid["verdict"] == "pay"
    assert invalid["valid"] is False
    assert invalid["message"] == "Inválido: el campo monto fue alterado después de firmarse."
    assert invalid["altered_fields"] == ["payment.amount"]


def test_the_server_check_takes_anything_and_never_fails(client: TestClient) -> None:
    junks: list[object] = [[], "hola", 3, {"format": "custodio-receipt/1"}]
    for junk in junks:
        response = client.post(f"{API}/receipts/verify", json=junk)
        assert response.status_code == 200, junk
        assert response.json()["valid"] is False


def test_the_example_receipt_is_signed_with_the_real_key_and_says_it_is_an_example(client: TestClient) -> None:
    example = client.get(f"{API}/receipts/example").json()

    assert example["body"]["workspace_id"] == "ejemplo"
    assert verify_receipt(example, public_key(client)).valid


def test_every_payment_in_the_ledger_went_through_the_guard(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    ledger = client.get(f"{API}/ledger", headers=workspace.headers).json()
    payments = [e for e in ledger if e["kind"] == "payment"]
    decided = {e["subject_id"]: e["seq"] for e in ledger if e["kind"] == "decision"}

    assert payments
    assert all(p["payload"]["execution_status"] == "simulated" for p in payments)
    assert all(decided[p["subject_id"]] < p["seq"] for p in payments)


def test_the_key_id_is_the_hash_of_the_public_key(client: TestClient) -> None:
    key = public_key(client)
    view = client.get(f"{API}/.well-known/custodio-receipt-key").json()

    assert view["key_id"] == "cust-" + hashlib.sha256(key.raw).hexdigest()[:16]


def test_a_later_policy_change_does_not_rewrite_where_an_earlier_payment_went(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    before = receipt(client, workspace, "F01")
    policy = client.get(f"{API}/policy", headers=workspace.headers).json()
    paid_to = before["body"]["payment"]["beneficiary_id"]
    for beneficiary in policy["beneficiaries"]:
        if beneficiary["id"] == paid_to:
            beneficiary["account_number"] = "000111222333"
    changed = client.put(f"{API}/policy", headers=workspace.headers, json=policy)
    assert changed.status_code == 200, changed.text

    assert receipt(client, workspace, "F01") == before


def test_no_receipt_is_signed_for_more_than_the_ledger_recorded(client: TestClient, runtime: Runtime) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    with runtime.database.session() as session:
        ctx = runtime.context(session)
        decision = records.decision(ctx, workspace.id, "F01")
        assert decision.amount is not None and decision.amount_base is not None
        inflated = decision.model_copy(
            update={"amount": decision.amount * 10, "amount_base": decision.amount_base * 10}
        )

        with pytest.raises(ReceiptUnavailable):
            receipt_service.issue(ctx, workspace.id, inflated, policy_service.current(ctx, workspace.id))
