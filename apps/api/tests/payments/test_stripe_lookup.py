"""Reading transfers back from Stripe (fake transport under the real SDK): found, missing, unreachable, cached."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from custodio.payments import CachedLookup, StripeApiLookup, StripeUnavailableError
from custodio.payments.stripe_lookup import PAGE_SIZE

from .stripe_fake import FakeStripe

WORKSPACE = {"workspace_id": "ws_a", "invoice_id": "F01"}


@dataclass
class Ticks:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now


def test_a_transfer_is_read_with_its_balance_transaction() -> None:
    fake = FakeStripe()
    sent = fake.add_transfer(120_050, WORKSPACE, destination="acct_andes")

    transfer = StripeApiLookup(fake.client()).transfer(sent["id"])

    assert transfer is not None
    assert (transfer.id, transfer.amount_cents, transfer.currency) == (sent["id"], 120_050, "usd")
    assert transfer.destination == "acct_andes"
    assert transfer.livemode is False
    assert (transfer.workspace_id, transfer.invoice_id) == ("ws_a", "F01")
    assert transfer.balance is not None and transfer.balance.amount_cents == -120_050
    assert transfer.raw["id"] == sent["id"]
    [request] = fake.requests
    assert request.form["expand[0]"] == "balance_transaction"


def test_a_transfer_stripe_does_not_have_is_none() -> None:
    assert StripeApiLookup(FakeStripe().client()).transfer("tr_doesnotexist") is None


def test_an_id_that_is_not_a_transfer_id_never_reaches_stripe() -> None:
    fake = FakeStripe()

    assert StripeApiLookup(fake.client()).transfer("../v1/balance") is None
    assert fake.requests == []


def test_stripe_unreachable_is_one_typed_error_without_stripe_s_message() -> None:
    fake = FakeStripe(unreachable=True)

    with pytest.raises(StripeUnavailableError) as raised:
        StripeApiLookup(fake.client()).transfer("tr_fake0001")
    assert str(raised.value) == ""


def test_a_rejected_key_is_unavailable_not_missing_and_never_echoes_stripe_s_message() -> None:
    fake = FakeStripe()
    sent = fake.add_transfer(100, WORKSPACE)
    fake.fail_next_read(f"/v1/transfers/{sent['id']}", 401, "invalid_request_error", "Invalid API Key sk_test_cust…")

    with pytest.raises(StripeUnavailableError) as raised:
        StripeApiLookup(fake.client()).transfer(sent["id"])
    assert "sk_test" not in str(raised.value)


def test_listing_follows_every_page_since_the_given_time() -> None:
    fake = FakeStripe()
    for _ in range(PAGE_SIZE + 5):
        fake.add_transfer(100, WORKSPACE)
    since = StripeApiLookup(fake.client()).transfer(fake.transfers[0]["id"])
    assert since is not None

    listing = StripeApiLookup(fake.client()).transfers_since(since.created)

    assert listing.complete is True
    assert len(listing.transfers) == PAGE_SIZE + 5
    assert len({t.id for t in listing.transfers}) == PAGE_SIZE + 5


def test_the_cache_answers_a_reload_and_asks_again_once_it_expires() -> None:
    fake = FakeStripe()
    sent = fake.add_transfer(100, WORKSPACE)
    ticks = Ticks()
    lookup = CachedLookup(StripeApiLookup(fake.client()), ttl_seconds=10, clock=ticks)

    lookup.transfer(sent["id"])
    ticks.now = 9
    lookup.transfer(sent["id"])
    assert len(fake.requests) == 1

    ticks.now = 10
    lookup.transfer(sent["id"])
    assert len(fake.requests) == 2


def test_a_failure_is_never_cached() -> None:
    fake = FakeStripe(unreachable=True)
    sent = fake.add_transfer(100, WORKSPACE)
    lookup = CachedLookup(StripeApiLookup(fake.client()), clock=Ticks())

    with pytest.raises(StripeUnavailableError):
        lookup.transfer(sent["id"])
    fake.unreachable = False

    found = lookup.transfer(sent["id"])
    assert found is not None and found.id == sent["id"]
