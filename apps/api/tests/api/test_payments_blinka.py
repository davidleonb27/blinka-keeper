"""The panel's payments become the exact instruction Blinka would receive; nothing leaves Custodio."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.contracts import Policy
from custodio.db import Database
from custodio.payments import BLINKA_SIMULATED, choose_rail
from custodio.services import payment_service, policy_service, records
from custodio.services.context import RateLimits, Runtime
from custodio.services.lanes import Lanes

from .conftest import MutableClock
from .helpers import assert_ledger_valid, new_workspace, process


@pytest.fixture
def runtime(database: Database, lanes: Lanes, clock: MutableClock, limits: RateLimits) -> Runtime:
    return Runtime(
        database=database,
        lanes=lanes,
        clock=clock,
        limits=limits,
        public_base_url="https://custodio.test",
        payment_rail=choose_rail(BLINKA_SIMULATED, None),
    )


def paid(batch: dict[str, Any]) -> list[dict[str, Any]]:
    return [d for d in batch["batch"]["decisions"] if d["execution"] is not None]


def test_each_paid_invoice_carries_the_instruction_blinka_would_receive(client: TestClient) -> None:
    workspace = new_workspace(client)
    policy = Policy.model_validate(client.get("/api/v1/policy", headers=workspace.headers).json())
    registered = {b.id: b for b in policy.beneficiaries}

    payments = paid(process(client, workspace))

    assert payments
    for decision in payments:
        execution = decision["execution"]
        instruction = execution["instruction"]
        beneficiary = registered[decision["beneficiary_id"]]
        assert execution["rail"] == "blinka_simulated"
        assert execution["status"] == "simulated"
        assert instruction["reference"] == f"https://custodio.test/acta/{decision['invoice_id']}"
        assert instruction["idempotency_key"] == f"{workspace.id}:{decision['invoice_id']}"
        assert instruction["currency"] == decision["currency"]
        assert instruction["amount"] == decision["amount"]
        assert instruction["account_number"] == beneficiary.account_number
        assert instruction["beneficiary_name"] == beneficiary.name


def test_the_acta_and_the_stored_execution_keep_the_instruction(client: TestClient, runtime: Runtime) -> None:
    workspace = new_workspace(client)
    [first, *_] = paid(process(client, workspace))
    invoice_id = first["invoice_id"]

    acta = client.get(f"/api/v1/decisions/{invoice_id}", headers=workspace.headers).json()
    with runtime.database.session() as session:
        ctx = runtime.context(session)
        decision = records.decision(ctx, workspace.id, invoice_id)
        again = payment_service.execute(ctx, workspace.id, decision, policy_service.current(ctx, workspace.id))

    assert acta["decision"]["execution"] == first["execution"]
    assert again == decision.execution
    assert again is not None and again.instruction is not None


def test_the_ledger_records_the_blinka_rail_and_stays_valid(client: TestClient) -> None:
    workspace = new_workspace(client)
    [first, *_] = paid(process(client, workspace))

    acta = client.get(f"/api/v1/decisions/{first['invoice_id']}", headers=workspace.headers).json()

    [payment] = [entry for entry in acta["ledger"] if entry["kind"] == "payment"]
    assert payment["payload"]["rail"] == "blinka_simulated"
    assert payment["payload"]["execution_status"] == "simulated"
    assert payment["payload"]["livemode"] is False
    assert_ledger_valid(client, workspace)


def test_health_reports_the_blinka_rail(client: TestClient) -> None:
    assert client.get("/api/v1/health").json()["payment_rail"] == "blinka_simulated"
