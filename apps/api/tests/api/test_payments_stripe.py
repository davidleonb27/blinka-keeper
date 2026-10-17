"""The panel's payments leave through the Stripe test-mode rail (fake transport under the real SDK)."""

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.api.app import create_app
from custodio.contracts import Decision
from custodio.db import Database
from custodio.payments import STRIPE_TEST, RailChoice, StripeAccountTable, StripeTestRail
from custodio.payments.port import Clock
from custodio.services import payment_service, policy_service, records, workspace_service
from custodio.services.context import RateLimits, Runtime
from custodio.services.lanes import Lanes
from tests.payments.stripe_fake import FakeStripe

from .conftest import MutableClock
from .doubles import invoice_text
from .helpers import Workspace, assert_ledger_valid, new_workspace, process, upload_text

APPROVER = {"approver": "Ana Gómez"}


@pytest.fixture
def stripe_http() -> FakeStripe:
    return FakeStripe()


def stripe_choice(fake: FakeStripe) -> RailChoice:
    client = fake.client()

    def build(session: Any, clock: Clock) -> StripeTestRail:
        return StripeTestRail(client, StripeAccountTable(session, clock), clock=clock)

    return RailChoice(name=STRIPE_TEST, build=build)


@pytest.fixture
def runtime(
    database: Database, lanes: Lanes, clock: MutableClock, limits: RateLimits, stripe_http: FakeStripe
) -> Runtime:
    return Runtime(
        database=database,
        lanes=lanes,
        clock=clock,
        limits=limits,
        public_base_url="https://custodio.test",
        payment_rail=stripe_choice(stripe_http),
    )


def decided(batch: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {decision["invoice_id"]: decision for decision in batch["batch"]["decisions"]}


def acta(client: TestClient, workspace: Workspace, invoice_id: str) -> dict[str, Any]:
    response = client.get(f"/api/v1/decisions/{invoice_id}", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_a_decided_payment_goes_out_through_stripe_and_the_acta_shows_its_receipt(
    client: TestClient, stripe_http: FakeStripe
) -> None:
    workspace = new_workspace(client)

    decisions = decided(process(client, workspace))

    [transfer] = stripe_http.posts("/v1/transfers")
    execution = decisions["F01"]["execution"]
    assert decisions["F01"]["status"] == "paid_auto"
    assert execution["rail"] == "stripe_test"
    assert execution["status"] == "executed"
    assert execution["external_id"] == stripe_http.transfers[0]["id"]
    assert execution["dashboard_url"].endswith(execution["external_id"])
    assert decisions["F02"]["execution"] is None
    assert decisions["F03"]["execution"] is None
    assert acta(client, workspace, "F01")["decision"]["execution"] == execution
    assert transfer.idempotency_key == f"{workspace.id}:F01"
    assert transfer.form["metadata[acta_url]"] == "https://custodio.test/acta/F01"
    assert transfer.form["amount"] == "120000"


def test_the_payment_ledger_entry_records_the_rail_and_its_receipt(client: TestClient, stripe_http: FakeStripe) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    [payment] = [entry for entry in acta(client, workspace, "F01")["ledger"] if entry["kind"] == "payment"]

    assert payment["payload"]["rail"] == "stripe_test"
    assert payment["payload"]["execution_status"] == "executed"
    assert payment["payload"]["external_id"] == stripe_http.transfers[0]["id"]
    assert payment["payload"]["livemode"] is False
    assert_ledger_valid(client, workspace)


def test_each_supplier_gets_one_stripe_account_shared_by_every_workspace(
    client: TestClient, stripe_http: FakeStripe
) -> None:
    for _ in range(2):
        process(client, new_workspace(client))

    assert len(stripe_http.posts("/v1/accounts")) == 1
    assert len({transfer.form["destination"] for transfer in stripe_http.posts("/v1/transfers")}) == 1
    assert len(stripe_http.posts("/v1/transfers")) == 2


def test_an_approved_payment_goes_out_only_after_the_person_approves(
    client: TestClient, stripe_http: FakeStripe
) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    keys_before = [transfer.idempotency_key for transfer in stripe_http.posts("/v1/transfers")]

    approved = client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json=APPROVER).json()

    assert keys_before == [f"{workspace.id}:F01"]
    assert stripe_http.posts("/v1/transfers")[-1].idempotency_key == f"{workspace.id}:F02"
    assert approved["status"] == "paid_human"
    assert approved["execution"]["status"] == "executed"


def test_a_rejected_payment_never_reaches_stripe(client: TestClient, stripe_http: FakeStripe) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    rejected = client.post("/api/v1/decisions/F02/reject", headers=workspace.headers, json=APPROVER).json()

    assert rejected["execution"] is None
    assert len(stripe_http.posts("/v1/transfers")) == 1


def test_an_executed_payment_is_reused_and_never_sent_twice(
    client: TestClient, runtime: Runtime, stripe_http: FakeStripe
) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    with runtime.database.session() as session:
        ctx = runtime.context(session)
        decision = records.decision(ctx, workspace.id, "F01")
        again = payment_service.execute(ctx, workspace.id, decision, policy_service.current(ctx, workspace.id))
    retried = client.post("/api/v1/decisions/F01/execute", headers=workspace.headers)

    assert again == decision.execution
    assert retried.status_code == 200
    assert Decision.model_validate(retried.json()).execution == decision.execution
    assert len(stripe_http.posts("/v1/transfers")) == 1


def test_a_failed_payment_stays_paid_by_the_engine_and_a_retry_sends_it(
    client: TestClient, stripe_http: FakeStripe
) -> None:
    workspace = new_workspace(client)
    stripe_http.fail_next("/v1/transfers", 400, "invalid_request_error", "transfers_not_allowed")

    failed = decided(process(client, workspace))["F01"]
    retried = client.post("/api/v1/decisions/F01/execute", headers=workspace.headers)

    assert failed["status"] == "paid_auto"
    assert failed["execution"]["status"] == "failed"
    assert "transfers_not_allowed" in failed["execution"]["error"]
    assert retried.status_code == 200, retried.text
    assert retried.json()["execution"]["status"] == "executed"
    assert acta(client, workspace, "F01")["decision"]["execution"]["status"] == "executed"
    assert [t.idempotency_key for t in stripe_http.posts("/v1/transfers")] == [
        f"{workspace.id}:F01",
        f"{workspace.id}:F01:intento-2",
    ]
    assert len(stripe_http.transfers) == 1
    assert_ledger_valid(client, workspace)


def test_only_a_payment_whose_execution_failed_can_be_retried(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    held = client.post("/api/v1/decisions/F03/execute", headers=workspace.headers)
    pending = client.post("/api/v1/decisions/F02/execute", headers=workspace.headers)

    assert held.status_code == 409
    assert held.json()["code"] == "payment_not_retryable"
    assert pending.status_code == 409


def test_a_workspace_stops_paying_at_its_test_transfer_cap(runtime: Runtime, stripe_http: FakeStripe) -> None:
    capped = replace(runtime, limits=replace(runtime.limits, test_transfers_per_workspace=1))
    with TestClient(create_app(capped)) as capped_client:
        workspace = new_workspace(capped_client)
        upload_text(capped_client, workspace, invoice_text(number="FV-010", amount="900.00"))

        decisions = decided(process(capped_client, workspace))

    paid = [d for d in decisions.values() if d["status"] == "paid_auto"]
    assert [d["execution"]["status"] for d in paid] == ["executed", "failed"]
    assert "Tope de pagos de prueba alcanzado" in paid[1]["execution"]["error"]
    assert len(stripe_http.posts("/v1/transfers")) == 1


def test_the_deployment_stops_paying_at_its_daily_cap_until_the_next_utc_day(
    runtime: Runtime, clock: MutableClock, stripe_http: FakeStripe
) -> None:
    capped = replace(runtime, limits=replace(runtime.limits, test_transfers_per_day=1))
    with TestClient(create_app(capped)) as capped_client:
        process(capped_client, new_workspace(capped_client))
        second = new_workspace(capped_client)
        blocked = decided(process(capped_client, second))["F01"]["execution"]
        clock.advance(timedelta(days=1))
        retried = capped_client.post("/api/v1/decisions/F01/execute", headers=second.headers).json()

    assert "Tope de pagos de prueba alcanzado" in blocked["error"]
    assert retried["execution"]["status"] == "executed"
    assert len(stripe_http.transfers) == 2


def test_a_payment_stops_reaching_stripe_after_its_last_allowed_attempt(
    runtime: Runtime, stripe_http: FakeStripe
) -> None:
    capped = replace(runtime, limits=replace(runtime.limits, payment_attempts_per_invoice=2))
    for _ in range(3):
        stripe_http.fail_next("/v1/transfers", 400, "invalid_request_error", "transfers_not_allowed")
    with TestClient(create_app(capped)) as capped_client:
        workspace = new_workspace(capped_client)
        process(capped_client, workspace)
        second = capped_client.post("/api/v1/decisions/F01/execute", headers=workspace.headers).json()
        third = capped_client.post("/api/v1/decisions/F01/execute", headers=workspace.headers).json()

    assert "transfers_not_allowed" in second["execution"]["error"]
    assert third["execution"]["status"] == "failed"
    assert "máximo de 2 intentos" in third["execution"]["error"]
    assert len(stripe_http.posts("/v1/transfers")) == 2


def test_the_test_transfer_caps_are_forty_per_workspace_and_four_hundred_a_day() -> None:
    assert RateLimits().test_transfers_per_workspace == 40
    assert RateLimits().test_transfers_per_day == 400
    assert RateLimits().payment_attempts_per_invoice == 5


def test_health_reports_the_active_rail(client: TestClient) -> None:
    assert client.get("/api/v1/health").json()["payment_rail"] == "stripe_test"


def test_sandboxes_are_not_visitor_workspaces(runtime: Runtime) -> None:
    # The guard below the explicit flag: a sandbox workspace never executes, whoever calls decide.
    runtime.database.migrate()
    with runtime.database.session() as session:
        ctx = runtime.context(session)
        state, policy = runtime.lanes.demo_company()
        sandbox_id = workspace_service.create_sandbox(ctx, workspace_service.WorkspaceKind.CHALLENGE, state, policy)
        assert not payment_service.may_execute(workspace_service.get_sandbox(ctx, sandbox_id))
