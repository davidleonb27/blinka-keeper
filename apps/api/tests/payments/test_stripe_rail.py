from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from custodio.payments import STRIPE_TEST, PaymentOrder, StripeTestRail

from .stripe_fake import TEST_KEY, FakeStripe

NOW = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
ORDER = PaymentOrder(
    idempotency_key="ws-1:F01",
    workspace_id="ws-1",
    invoice_id="F01",
    beneficiary_id="B-NUBE",
    supplier_name="Nube Hosting S.A.S.",
    amount_base=Decimal("1200.00"),
    currency="USD",
    amount=Decimal("1200.00"),
    acta_url="https://custodio.test/acta/F01",
)
TOP_UP_MARGIN_CENTS = 100_000


class MemoryAccounts:
    def __init__(self) -> None:
        self.accounts: dict[tuple[str, str], str] = {}

    def find(self, beneficiary_id: str, name_key: str) -> str | None:
        return self.accounts.get((beneficiary_id, name_key))

    def remember(self, beneficiary_id: str, name_key: str, account_id: str) -> str:
        return self.accounts.setdefault((beneficiary_id, name_key), account_id)


def rail(fake: FakeStripe, accounts: MemoryAccounts | None = None) -> StripeTestRail:
    return StripeTestRail(fake.client(), accounts or MemoryAccounts(), clock=lambda: NOW)


def test_a_payment_goes_out_as_a_stripe_transfer_and_returns_its_receipt() -> None:
    fake = FakeStripe()

    receipt = rail(fake).execute(ORDER)

    [transfer] = fake.posts("/v1/transfers")
    assert receipt.rail == STRIPE_TEST
    assert receipt.status == "executed"
    assert receipt.external_id is not None and receipt.external_id.startswith("tr_")
    assert receipt.dashboard_url == f"https://dashboard.stripe.com/test/connect/transfers/{receipt.external_id}"
    assert receipt.executed_at == NOW
    assert receipt.error is None
    assert transfer.form["amount"] == "120000"
    assert transfer.form["currency"] == "usd"
    assert transfer.form["destination"].startswith("acct_")
    assert transfer.form["metadata[workspace_id]"] == "ws-1"
    assert transfer.form["metadata[invoice_id]"] == "F01"
    assert transfer.form["metadata[acta_url]"] == "https://custodio.test/acta/F01"


def test_the_transfer_carries_the_order_idempotency_key() -> None:
    fake = FakeStripe()

    rail(fake).execute(ORDER)

    assert [r.idempotency_key for r in fake.posts("/v1/transfers")] == ["ws-1:F01"]


def test_the_beneficiary_gets_a_verified_custom_test_account_once() -> None:
    fake = FakeStripe()
    accounts = MemoryAccounts()

    rail(fake, accounts).execute(ORDER)
    rail(fake, accounts).execute(replace(ORDER, idempotency_key="ws-2:F09", workspace_id="ws-2", invoice_id="F09"))

    [account] = fake.posts("/v1/accounts")
    expected = {
        "type": "custom",
        "country": "US",
        "capabilities[transfers][requested]": "true",
        "business_type": "individual",
        "individual[dob][day]": "1",
        "individual[dob][month]": "1",
        "individual[dob][year]": "1901",
        "individual[ssn_last_4]": "0000",
        "individual[address][line1]": "address_full_match",
        "external_account": "btok_us_verified",
        "business_profile[name]": "Nube Hosting S.A.S.",
    }
    assert expected.items() <= account.form.items()
    assert account.form["tos_acceptance[date]"].isdigit()
    assert account.form["tos_acceptance[ip]"]
    destinations = {r.form["destination"] for r in fake.posts("/v1/transfers")}
    assert destinations == set(accounts.accounts.values())
    assert len(destinations) == 1


def test_the_amount_is_rounded_to_cents() -> None:
    fake = FakeStripe()

    rail(fake).execute(replace(ORDER, amount_base=Decimal("1234.565")))

    assert fake.posts("/v1/transfers")[0].form["amount"] == "123457"


def test_an_empty_test_balance_is_topped_up_and_the_transfer_retried_once() -> None:
    fake = FakeStripe(balance_cents=20_000)

    receipt = rail(fake).execute(ORDER)

    [top_up] = fake.posts("/v1/payment_intents")
    assert receipt.status == "executed"
    assert top_up.form["amount"] == str(120_000 - 20_000 + TOP_UP_MARGIN_CENTS)
    assert top_up.form["currency"] == "usd"
    assert top_up.form["payment_method"] == "pm_card_bypassPending"
    assert top_up.form["confirm"] == "true"
    assert len(fake.posts("/v1/transfers")) == 2


def test_a_second_insufficient_balance_fails_cleanly() -> None:
    fake = FakeStripe()
    for _ in range(2):
        fake.fail_next("/v1/transfers", 400, "invalid_request_error", "balance_insufficient")

    receipt = rail(fake).execute(ORDER)

    assert receipt.status == "failed"
    assert receipt.external_id is None
    assert receipt.error is not None and "saldo" in receipt.error
    assert len(fake.posts("/v1/transfers")) == 2


def test_a_stripe_rejection_is_a_failed_receipt_in_spanish_without_secrets() -> None:
    fake = FakeStripe()
    fake.fail_next("/v1/accounts", 400, "invalid_request_error", "platform_account_required", f"Bad key {TEST_KEY}")

    receipt = rail(fake).execute(ORDER)

    assert receipt.status == "failed"
    assert receipt.rail == STRIPE_TEST
    assert receipt.error is not None
    assert "Stripe rechazó" in receipt.error
    assert "platform_account_required" in receipt.error
    assert TEST_KEY not in receipt.error
    assert fake.posts("/v1/transfers") == []


def test_an_unreachable_stripe_is_a_failed_receipt() -> None:
    fake = FakeStripe(unreachable=True)

    receipt = rail(fake).execute(ORDER)

    assert receipt.status == "failed"
    assert receipt.error is not None and "Stripe" in receipt.error


def test_a_payment_without_beneficiary_fails_without_calling_stripe() -> None:
    fake = FakeStripe()

    receipt = rail(fake).execute(replace(ORDER, beneficiary_id=None))

    assert receipt.status == "failed"
    assert fake.requests == []
