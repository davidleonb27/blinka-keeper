import logging
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from custodio.payments import SIMULATED, STRIPE_TEST, PaymentOrder, SimulatedRail, choose_rail

NOW = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
LIVE_KEY = "sk_live_" + "x" * 24
RESTRICTED_LIVE_KEY = "rk_live_" + "y" * 24


def test_the_simulated_rail_moves_no_money_and_says_so() -> None:
    order = PaymentOrder(
        idempotency_key="ws:F01",
        workspace_id="ws",
        invoice_id="F01",
        beneficiary_id="B-NUBE",
        supplier_name="Nube Hosting S.A.S.",
        amount_base=Decimal("1200"),
        currency="USD",
        amount=Decimal("1200"),
        acta_url="https://custodio.test/acta/F01",
    )

    receipt = SimulatedRail(clock=lambda: NOW).execute(order)

    assert receipt.rail == SIMULATED
    assert receipt.status == "simulated"
    assert receipt.external_id is None
    assert receipt.dashboard_url is None
    assert receipt.executed_at == NOW
    assert receipt.error is None


def test_the_simulated_rail_is_the_default() -> None:
    assert choose_rail("", None).name == SIMULATED
    assert choose_rail("simulated", "sk_test_abc").name == SIMULATED


def test_stripe_runs_only_when_asked_for_with_a_test_key() -> None:
    assert choose_rail("stripe_test", "sk_test_abc").name == STRIPE_TEST
    assert choose_rail("stripe_test", None).name == SIMULATED
    assert choose_rail("stripe_test", "pk_test_abc").name == SIMULATED


@pytest.mark.parametrize("live_key", [LIVE_KEY, RESTRICTED_LIVE_KEY])
def test_a_live_stripe_key_is_refused_and_never_logged(live_key: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        choice = choose_rail("stripe_test", live_key)

    assert choice.name == SIMULATED
    assert any("live" in record.getMessage() for record in caplog.records)
    assert all(live_key not in record.getMessage() for record in caplog.records)
    assert live_key[8:] not in caplog.text
