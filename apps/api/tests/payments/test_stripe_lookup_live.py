"""Sends one real 1 USD test-mode transfer and reads it back the way the acta does, then lists it the way /pagos does.

Runs only with CUSTODIO_LIVE_TESTS=1 and a sk_test_ STRIPE_SECRET_KEY.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import stripe

from custodio.payments import PaymentOrder, StripeApiLookup, StripeTestRail

from .test_stripe_rail import MemoryAccounts

KEY = os.environ.get("STRIPE_SECRET_KEY", "")
LISTING_MARGIN = timedelta(minutes=5)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("CUSTODIO_LIVE_TESTS") != "1", reason="live tests are opt-in"),
    pytest.mark.skipif(not KEY.startswith("sk_test_"), reason="needs a Stripe test-mode secret key"),
]


def test_a_real_test_transfer_is_proven_by_reading_it_back_from_stripe() -> None:
    run = uuid.uuid4().hex[:12]
    started = datetime.now(UTC)
    order = PaymentOrder(
        idempotency_key=f"live-proof-{run}:F01",
        workspace_id=f"live-proof-{run}",
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
    assert receipt.external_id is not None
    lookup = StripeApiLookup.with_key(KEY)

    transfer = lookup.transfer(receipt.external_id)
    listing = lookup.transfers_since(started - LISTING_MARGIN)

    assert transfer is not None
    assert (transfer.amount_cents, transfer.currency, transfer.livemode) == (100, "usd", False)
    assert (transfer.workspace_id, transfer.invoice_id) == (order.workspace_id, "F01")
    assert transfer.balance is not None
    assert receipt.external_id in {t.id for t in listing.transfers}
    assert lookup.transfer("tr_custodio_does_not_exist") is None
