import json
from decimal import Decimal
from typing import get_args

from fastapi.testclient import TestClient

from custodio.config import Settings
from custodio.contracts import RULES, Approval, Approver, Policy, RuleEffect
from main import app


def test_the_catalogue_has_fifteen_rules_in_order() -> None:
    assert [rule.id for rule in RULES] == [f"R{i}" for i in range(1, 16)]
    assert len({rule.key for rule in RULES}) == 15
    assert [(rule.key, rule.effect) for rule in RULES[12:]] == [
        ("bank_details", RuleEffect.ESCALATE),
        ("sanctions", RuleEffect.ESCALATE),
        ("out_of_band", RuleEffect.ESCALATE),
    ]


def test_only_the_payment_controls_let_a_payment_through_when_they_had_nothing_to_check() -> None:
    assert {rule.id for rule in RULES if rule.neutral_when_skipped} == {"R13", "R14", "R15"}


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


def test_health_reports_only_the_providers_in_use() -> None:
    body = TestClient(app).get("/api/v1/health").json()

    assert set(body) == {"status", "version", "anthropic", "payment_rail", "sanctions_list_date"}
    assert body["payment_rail"] == "simulated"  # Stripe only with CUSTODIO_PAYMENT_RAIL=stripe_test and a test key


def test_settings_carry_no_retired_integrations() -> None:
    retired = {"gemini_model", "telegram_bot_token_present"}

    assert retired.isdisjoint(Settings.model_fields)
    assert not hasattr(Settings, "gemini_configured")


def test_approvals_are_web_or_api_only() -> None:
    assert set(Approver.model_fields) == {"name", "role", "email"}
    assert get_args(Approval.model_fields["channel"].annotation) == ("web", "api")


def test_health_dates_the_ofac_copy_in_use() -> None:
    body = TestClient(app).get("/api/v1/health").json()
    assert body["sanctions_list_date"] == "2026-10-15"
