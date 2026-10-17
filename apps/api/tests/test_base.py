import json
from decimal import Decimal

from fastapi.testclient import TestClient

from custodio.contracts import RULES, Policy, RuleEffect
from main import app


def test_the_catalogue_has_twelve_rules_in_order() -> None:
    assert [rule.id for rule in RULES] == [f"R{i}" for i in range(1, 13)]
    assert len({rule.key for rule in RULES}) == 12


def test_hold_rules_are_the_ones_the_agent_can_stop_alone() -> None:
    holds = {rule.id for rule in RULES if rule.effect is RuleEffect.HOLD}
    assert holds == {"R4", "R5", "R8", "R12"}


def test_default_policy_matches_the_prototype() -> None:
    policy = Policy()
    assert policy.approval_threshold == Decimal("5000")
    assert policy.per_payment_limit == Decimal("12000")
    assert policy.period_budget == Decimal("37000")
    assert policy.reserve == Decimal("60000")


def test_amounts_are_numbers_on_the_wire() -> None:
    payload = json.loads(Policy().model_dump_json())
    assert payload["approval_threshold"] == 5000.0


def test_health_answers_under_the_public_prefix() -> None:
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
