from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from custodio.contracts import Beneficiary
from custodio.payments import BLINKA_SIMULATED, BlinkaRail, PaymentOrder

NOW = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
PULSO = Beneficiary(
    id="b2",
    name="Pulso Software Inc.",
    tax_id="84-2219034",
    country="US",
    bank_name="Mercury",
    account_number="202211887766",
    currency="USD",
)
ORDER = PaymentOrder(
    idempotency_key="ws-1:F05",
    workspace_id="ws-1",
    invoice_id="F05",
    beneficiary_id="b2",
    supplier_name="Pulso Software Inc.",
    amount_base=Decimal("840.00"),
    currency="USD",
    amount=Decimal("840.00"),
    acta_url="https://custodio.test/acta/F05",
    beneficiary=PULSO,
)


def rail() -> BlinkaRail:
    return BlinkaRail(clock=lambda: NOW)


def paying(currency: str, amount: str, *, country: str | None = "US", base: str | None = None) -> PaymentOrder:
    beneficiary = PULSO.model_copy(update={"country": country, "currency": currency})
    return replace(
        ORDER,
        currency=currency,
        amount=Decimal(amount),
        amount_base=Decimal(base or amount),
        beneficiary=beneficiary,
    )


def test_a_domestic_dollar_payment_becomes_an_ach_instruction_for_blinka() -> None:
    receipt = rail().execute(ORDER)

    assert receipt.rail == BLINKA_SIMULATED
    assert receipt.status == "simulated"
    assert receipt.executed_at == NOW
    assert receipt.external_id is None
    assert receipt.error is None
    assert receipt.instruction is not None
    assert receipt.instruction.model_dump() == {
        "network": "ach",
        "amount": Decimal("840.00"),
        "currency": "USD",
        "beneficiary_name": "Pulso Software Inc.",
        "beneficiary_tax_id": "84-2219034",
        "beneficiary_country": "US",
        "bank_name": "Mercury",
        "account_number": "202211887766",
        "reference": "https://custodio.test/acta/F05",
        "idempotency_key": "ws-1:F05",
    }


@pytest.mark.parametrize(
    ("amount", "network"),
    [("10000.00", "ach"), ("10000.01", "wire"), ("48000", "wire")],
)
def test_dollars_above_ten_thousand_go_by_wire(amount: str, network: str) -> None:
    receipt = rail().execute(paying("USD", amount))

    assert receipt.instruction is not None
    assert receipt.instruction.network == network


@pytest.mark.parametrize("country", ["CO", "AR", None])
def test_dollars_to_a_beneficiary_outside_the_us_go_by_wire(country: str | None) -> None:
    receipt = rail().execute(paying("USD", "840", country=country))

    assert receipt.instruction is not None
    assert receipt.instruction.network == "wire"


@pytest.mark.parametrize(
    ("currency", "country", "network"),
    [("COP", "CO", "bre_b"), ("MXN", "MX", "spei"), ("BRL", "BR", "pix"), ("cop", "CO", "bre_b")],
)
def test_local_currencies_go_through_their_local_network(currency: str, country: str, network: str) -> None:
    receipt = rail().execute(paying(currency, "2600000", country=country, base="650"))

    assert receipt.status == "simulated"
    assert receipt.instruction is not None
    assert receipt.instruction.network == network
    assert receipt.instruction.currency == currency.upper()
    assert receipt.instruction.amount == Decimal("2600000")


def test_an_unsupported_currency_fails_with_a_clear_reason_and_no_instruction() -> None:
    receipt = rail().execute(paying("EUR", "1500", country="DE"))

    assert receipt.rail == BLINKA_SIMULATED
    assert receipt.status == "failed"
    assert receipt.instruction is None
    assert receipt.error is not None
    assert "EUR" in receipt.error
    assert all(name in receipt.error for name in ("ACH", "Bre-B", "SPEI", "Pix"))


def test_a_payment_without_a_registered_beneficiary_fails_without_an_instruction() -> None:
    receipt = rail().execute(replace(ORDER, beneficiary_id=None, beneficiary=None))

    assert receipt.status == "failed"
    assert receipt.instruction is None
    assert receipt.error is not None and "beneficiario" in receipt.error


def test_a_payment_without_a_positive_amount_fails_without_an_instruction() -> None:
    receipt = rail().execute(paying("USD", "0"))

    assert receipt.status == "failed"
    assert receipt.instruction is None
