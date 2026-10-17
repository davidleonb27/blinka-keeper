"""Earned autonomy through the API: risk signals and approvals write trust entries, and the caps come back from them."""

from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.api.app import create_app
from custodio.payments import STRIPE_TEST, RailChoice
from custodio.payments.port import Clock
from custodio.services.context import Runtime
from custodio.services.lanes import Lanes

from .doubles import model_free_lanes
from .helpers import Workspace, assert_ledger_valid, new_workspace, process

APPROVER = {"approver": "Ana Gómez"}
SUPERVISED_BY_THE_DEMO = {"b3": "R6", "b4": "R5", "b5": "R5", "b10": "R6", "b16": "R4", "b27": "R2"}


def refuse_stripe(_: Any, __: Clock) -> Any:
    raise AssertionError("the simulated month must never reach Stripe")


@pytest.fixture
def lanes() -> Lanes:
    return model_free_lanes()


@pytest.fixture
def stripe_client(runtime: Runtime) -> Iterator[TestClient]:
    """A deployment that pays through Stripe, where Stripe must never be reached by the simulated month."""
    refusing = replace(runtime, payment_rail=RailChoice(name=STRIPE_TEST, build=refuse_stripe))
    with TestClient(create_app(refusing)) as test_client:
        yield test_client


@pytest.fixture
def workspace(client: TestClient) -> Workspace:
    return new_workspace(client)


def trust(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    response = client.get("/api/v1/trust", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def suppliers(overview: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {supplier["beneficiary_id"]: supplier for supplier in overview["suppliers"]}


def ledger(client: TestClient, workspace: Workspace) -> list[dict[str, Any]]:
    response = client.get("/api/v1/ledger", headers=workspace.headers)
    assert response.status_code == 200, response.text
    entries: list[dict[str, Any]] = response.json()
    return entries


def simulate(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    """Through a Stripe deployment: the month must still pay on the simulated rail."""
    response = client.post("/api/v1/trust/simulate", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_a_new_workspace_has_no_trust_history_and_keeps_the_policy_threshold(
    client: TestClient, workspace: Workspace
) -> None:
    overview = trust(client, workspace)
    assert (overview["floor"], overview["ceiling"], overview["policy_threshold"]) == (0, 12000, 5000)
    assert overview["clean_payments_to_earn"] == 3
    assert overview["autonomy"] == []
    andes = suppliers(overview)["b1"]
    assert andes["has_history"] is False
    assert andes["cap"] == 5000
    assert andes["timeline"] == []


def test_every_risk_signal_of_the_demo_batch_sends_its_supplier_back_to_supervised(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    overview = suppliers(trust(client, workspace))
    for supplier, rule_id in SUPERVISED_BY_THE_DEMO.items():
        assert overview[supplier]["supervised"] is True, supplier
        assert overview[supplier]["cap"] == 0
        assert overview[supplier]["last_incident"]["rule_id"] == rule_id
        assert overview[supplier]["clean_needed"] == 3
    paredes = overview["b16"]
    [revoked] = paredes["timeline"]
    assert revoked["kind"] == "trust_revoked"
    assert revoked["invoice_id"] == "F-023"
    assert (revoked["cap_before"], revoked["cap_after"]) == (5000, 0)
    entry = next(e for e in ledger(client, workspace) if e["seq"] == revoked["seq"])
    assert entry["hash"] == revoked["hash"]
    assert entry["subject_id"] == "b16"
    assert overview["b1"]["has_history"] is False
    assert_ledger_valid(client, workspace)


def test_the_autonomy_series_counts_what_the_agent_decided_alone_each_day(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    overview = trust(client, workspace)
    days = overview["autonomy"]
    assert days[0]["day"] == "2026-09-28"
    total = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()["metrics"]["total"]
    assert sum(day["decisions"] for day in days) == total
    assert sum(day["decided_alone"] for day in days) == round(overview["autonomy_rate"] * total)


def test_a_payment_a_person_approves_without_a_risk_signal_earns_trust_once(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    approved = client.post("/api/v1/decisions/F-029/approve", headers=workspace.headers, json=APPROVER)
    assert approved.json()["status"] == "paid_human"  # Estudio Lumbre: the person confirmed the currency (R1)
    lumbre = suppliers(trust(client, workspace))["b25"]
    [raised] = lumbre["timeline"]
    assert raised["kind"] == "trust_raised"
    assert raised["invoice_id"] == "F-029"
    assert lumbre["clean_streak"] == 1
    assert lumbre["cap"] == 5000  # one clean payment never lowers the policy's cap
    assert "Ana Gómez aprobó" in raised["reason"]


def test_approving_a_decision_with_a_risk_signal_does_not_write_the_incident_twice(
    client: TestClient, workspace: Workspace
) -> None:
    process(client, workspace)
    client.post("/api/v1/decisions/F-022/approve", headers=workspace.headers, json=APPROVER)
    pixel = suppliers(trust(client, workspace))["b3"]
    assert [step["kind"] for step in pixel["timeline"]] == ["trust_revoked"]
    assert pixel["supervised"] is True


def test_the_simulated_month_raises_autonomy_and_a_fraud_attempt_knocks_it_down(stripe_client: TestClient) -> None:
    client = stripe_client
    workspace = new_workspace(client)
    result = simulate(client, workspace)
    assert result["created"] is True
    assert (result["seed"], result["days"]) == (1330, 30)
    cumulus = suppliers(result["trust"])["b10"]
    kinds = [step["kind"] for step in cumulus["timeline"]]
    fraud = kinds.index("trust_revoked", 2)  # after the two risk signals of the demo batch
    assert kinds[2:fraud] == ["trust_raised"] * (fraud - 2)
    assert max(step["cap_after"] for step in cumulus["timeline"][:fraud]) > 0
    assert cumulus["timeline"][fraud]["rule_id"] == "R4"
    assert cumulus["timeline"][fraud]["cap_after"] == 0
    simulated_days = [day for day in result["trust"]["autonomy"] if day["day"] >= result["start"]]
    assert len(simulated_days) >= 10
    entries = ledger(client, workspace)
    [marker] = [e for e in entries if e["kind"] == "simulation"]
    assert float(marker["payload"]["inflow_base"]) == result["inflow_base"]
    payments = [e for e in entries if e["kind"] == "payment" and e["payload"]["rail"] is not None]
    assert payments and {e["payload"]["rail"] for e in payments} == {"simulated"}
    assert_ledger_valid(client, workspace)


def test_a_supervised_supplier_shows_why_its_invoices_wait_for_a_person(stripe_client: TestClient) -> None:
    client = stripe_client
    workspace = new_workspace(client)
    simulate(client, workspace)
    decisions = client.get("/api/v1/decisions", headers=workspace.headers).json()
    after_fraud = [
        item["decision"]
        for item in decisions
        if item["decision"]["beneficiary_id"] == "b10" and (item["decision"]["trust"] or {}).get("supervised")
    ]
    assert after_fraud
    r9 = next(rule for rule in after_fraud[-1]["rules"] if rule["rule_id"] == "R9")
    assert r9["outcome"] == "escalate"
    assert "se ha ganado" in r9["reason"]


def test_simulating_twice_changes_nothing(stripe_client: TestClient) -> None:
    client = stripe_client
    workspace = new_workspace(client)
    first = simulate(client, workspace)
    length = len(ledger(client, workspace))
    again = simulate(client, workspace)
    assert again["created"] is False
    assert len(ledger(client, workspace)) == length
    assert again["trust"] == first["trust"]


def test_only_the_demo_workspace_can_simulate_a_month(client: TestClient) -> None:
    blank = new_workspace(client, mode="blank")
    response = client.post("/api/v1/trust/simulate", headers=blank.headers)
    assert response.status_code == 409


def test_the_simulated_month_leaves_the_real_scheduled_payments_on_their_day(stripe_client: TestClient) -> None:
    client = stripe_client
    workspace = new_workspace(client)
    simulate(client, workspace)
    calendar = client.get("/api/v1/schedule", headers=workspace.headers).json()
    assert "F-024" in {item["invoice_id"] for item in calendar["items"]}  # due on 23 October, in real time


def test_the_simulated_month_is_the_same_in_every_demo_workspace(stripe_client: TestClient) -> None:
    def replay() -> dict[str, Any]:
        workspace = new_workspace(stripe_client)
        result = simulate(stripe_client, workspace)
        for supplier in result["trust"]["suppliers"]:
            steps = [*supplier["timeline"], *([supplier["last_incident"]] if supplier["last_incident"] else [])]
            for step in steps:
                del step["hash"]
        return result

    assert replay() == replay()
