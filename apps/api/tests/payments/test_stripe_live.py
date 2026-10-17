"""Sends one real 1 USD test-mode transfer. Runs only with CUSTODIO_LIVE_TESTS=1 and a sk_test_ STRIPE_SECRET_KEY."""

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import stripe

from custodio.payments import PaymentOrder, StripeTestRail

from .test_stripe_rail import MemoryAccounts

KEY = os.environ.get("STRIPE_SECRET_KEY", "")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("CUSTODIO_LIVE_TESTS") != "1", reason="live tests are opt-in"),
    pytest.mark.skipif(not KEY.startswith("sk_test_"), reason="needs a Stripe test-mode secret key"),
]


def test_one_dollar_reaches_a_test_connected_account() -> None:
    run = uuid.uuid4().hex[:12]
    order = PaymentOrder(
        idempotency_key=f"live-{run}:F01",
        workspace_id=f"live-{run}",
        invoice_id="F01",
        beneficiary_id=f"B-LIVE-{run}",
        supplier_name="Proveedor de prueba Custodio",
        amount_base=Decimal("1.00"),
        currency="USD",
        amount=Decimal("1.00"),
        acta_url="https://custodio.test/acta/F01",
    )

    receipt = StripeTestRail(stripe.StripeClient(KEY), MemoryAccounts(), clock=lambda: datetime.now(UTC)).execute(order)

    assert receipt.status == "executed", receipt.error
    assert receipt.external_id is not None and receipt.external_id.startswith("tr_")
