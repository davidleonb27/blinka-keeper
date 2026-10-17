"""The payment calendar through the API: approved payments wait for their day and go out through the rail then."""

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.services.lanes import Lanes, production_lanes

from .conftest import MutableClock
from .helpers import Workspace, assert_ledger_valid, new_workspace, process

RESERVE_ABOVE_THE_CASH = 70000


@pytest.fixture
def lanes() -> Lanes:
    return production_lanes()  # the real engine and auditor; nothing here reads a document or calls a model


@pytest.fixture
def workspace(client: TestClient) -> Workspace:
    return new_workspace(client)


def schedule(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    response = client.get("/api/v1/schedule", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def run_due(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    response = client.post("/api/v1/schedule/run-due", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["invoice_id"]: item for item in items}


def test_an_empty_workspace_has_an_empty_calendar_with_the_yield_assumption_labelled(
    client: TestClient, workspace: Workspace
) -> None:
    calendar = schedule(client, workspace)
    assert calendar["items"] == []
    assert calendar["horizon_days"] == 45
    assert calendar["apy"] == 4.0
    assert "supuesto configurable" in calendar["apy_note"]
    assert "CUSTODIO_TREASURY_YIELD_APY" in calendar["apy_note"]
    assert len(calendar["balance"]) == 46
    assert calendar["captured"]["total"] == 0


def test_approved_payments_wait_for_their_due_date_and_overdue_ones_go_out_now(
    client: TestClient, workspace: Workspace
) -> None:
    decisions = {d["invoice_id"]: d for d in process(client, workspace)["batch"]["decisions"]}
    assert decisions["F-004"]["execution"]["status"] == "simulated"  # due on 15 October: already overdue
    assert decisions["F-024"]["status"] == "paid_auto"
    assert decisions["F-024"]["execution"] is None  # due on 23 October
    items = by_id(schedule(client, workspace)["items"])
    assert "F-004" not in items
    lucia = items["F-024"]
    assert (lucia["pay_on"], lucia["due_date"], lucia["timing"]) == ("2026-10-23", "2026-10-23", "on_due")
    assert lucia["rail"] == "simulated"
    assert "no antes" in lucia["reason"]


def test_an_early_payment_discount_moves_the_payment_to_the_discounts_last_day(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    items = by_id(schedule(client, workspace)["items"])
    rent = items["F-027"]  # Oficinas Chapinero: 1/10, due on 24 October
    assert (rent["pay_on"], rent["timing"]) == ("2026-10-19", "discount")
    assert rent["discount_base"] > 0
    coffee = items["F-036"]  # Café Origen: 2/10, due on 30 October
    assert (coffee["pay_on"], coffee["timing"]) == ("2026-10-25", "discount")


def test_the_projected_balance_counts_the_cash_still_in_the_account_and_never_goes_under_the_reserve(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    calendar = schedule(client, workspace)
    waiting = sum(item["amount_base"] for item in calendar["items"])
    summary = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()
    assert calendar["cash"] == pytest.approx(summary["balance"] + waiting)
    assert calendar["balance"][0]["balance"] == pytest.approx(calendar["cash"])
    assert calendar["balance"][-1]["balance"] == pytest.approx(summary["balance"])
    assert min(point["balance"] for point in calendar["balance"]) >= calendar["reserve"]


def test_running_what_is_due_pays_it_through_the_rail_once(
    client: TestClient, workspace: Workspace, clock: MutableClock
) -> None:
    process(client, workspace)
    clock.advance(timedelta(days=2))  # 19 October
    ran = run_due(client, workspace)
    executed = {d["invoice_id"]: d for d in ran["executed"]}
    assert {"F-015", "F-017", "F-027"} <= set(executed)
    assert all(d["execution"]["status"] == "simulated" for d in executed.values())
    assert "F-024" not in executed
    assert not set(executed) & set(by_id(ran["schedule"]["items"]))
    acta = client.get("/api/v1/decisions/F-027", headers=workspace.headers).json()
    assert acta["decision"]["execution"]["status"] == "simulated"
    payment = [e for e in acta["ledger"] if e["kind"] == "payment"][-1]
    assert payment["payload"]["scheduled"] is True
    assert float(payment["payload"]["discount_base"]) > 0
    assert run_due(client, workspace)["executed"] == []
    assert_ledger_valid(client, workspace)


def test_the_value_captured_this_month_adds_discounts_and_yield(client: TestClient, workspace: Workspace) -> None:
    process(client, workspace)
    captured = schedule(client, workspace)["captured"]
    assert (captured["year"], captured["month"]) == (2026, 10)
    assert captured["discounts"] > 0
    assert captured["treasury_yield"] > 0
    assert captured["total"] == pytest.approx(
        captured["discounts"] + captured["late_fees_avoided"] + captured["treasury_yield"]
    )


def test_when_the_reserve_rises_over_the_cash_the_payments_wait_and_say_why(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    policy = client.get("/api/v1/policy", headers=workspace.headers).json()
    applied = client.put(
        "/api/v1/policy", headers=workspace.headers, json={**policy, "reserve": RESERVE_ABOVE_THE_CASH}
    )
    assert applied.status_code == 200, applied.text
    calendar = schedule(client, workspace)
    assert calendar["items"] == []
    assert calendar["waiting"]
    assert all(item["pay_on"] is None and "reserva" in item["reason"] for item in calendar["waiting"])
    assert run_due(client, workspace)["executed"] == []


def test_a_payment_intent_is_never_scheduled_because_the_agent_that_sent_it_pays_it(
    client: TestClient, workspace: Workspace
) -> None:
    intent = {
        "agent": "erp-bot",
        "beneficiary_name": "Joaquín Méndez",
        "beneficiary_tax_id": "20-38455120-7",
        "bank_name": "Banco Nación",
        "account_number": "0110-3471",
        "amount": 3600,
        "currency": "USD",
        "invoice_number": "JM-2026-10",
    }
    response = client.post("/api/v1/firewall/intents", headers=workspace.bearer, json=intent)
    assert response.json()["decision"]["status"] == "paid_auto", response.text
    calendar = schedule(client, workspace)
    assert (calendar["items"], calendar["waiting"]) == ([], [])
