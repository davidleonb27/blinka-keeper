"""The guard at the point of payment: no signed receipt of a decision to pay exactly this, no transfer."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from custodio.contracts import Beneficiary
from custodio.payments import GuardedRail, PaymentOrder, PaymentReceipt
from custodio.receipts import DecisionReceipt, ReceiptBody, account_fingerprint, sign_receipt

from ..receipts.builders import fixed_signer, other_signer, sample_body

NOW = datetime(2026, 10, 17, 15, 0, tzinfo=UTC)
SIGNER = fixed_signer()
ANDES = Beneficiary(
    id="b-andes",
    name="Andes Código S.A.S.",
    tax_id="900123456-7",
    country="US",
    bank_name="Mercury",
    account_number="000123456789",
    currency="USD",
)


@dataclass
class RecordingRail:
    calls: list[PaymentOrder] = field(default_factory=list)
    name: str = "simulated"

    def execute(self, order: PaymentOrder) -> PaymentReceipt:
        self.calls.append(order)
        return PaymentReceipt(rail="simulated", status="simulated", executed_at=NOW)


def body(**changes: object) -> ReceiptBody:
    base = sample_body(SIGNER.key_id)
    assert base.payment is not None
    payment = base.payment.model_copy(update={"account_sha256": account_fingerprint(ANDES.account_number)})
    return base.model_copy(update={"payment": payment, **changes})


def signed(receipt_body: ReceiptBody | None = None) -> DecisionReceipt:
    return sign_receipt(receipt_body or body(), SIGNER)


def order(receipt: DecisionReceipt | None) -> PaymentOrder:
    return PaymentOrder(
        idempotency_key="ws-ejemplo:INV-0001",
        workspace_id="ws-ejemplo",
        invoice_id="INV-0001",
        beneficiary_id="b-andes",
        supplier_name=ANDES.name,
        amount_base=Decimal("4200.00"),
        currency="USD",
        amount=Decimal("4200.00"),
        acta_url="https://custodio.test/acta/INV-0001",
        beneficiary=ANDES,
        decision_receipt=receipt,
    )


def guarded() -> tuple[GuardedRail, RecordingRail]:
    inner = RecordingRail()
    return GuardedRail(inner=inner, key=SIGNER.public_key, clock=lambda: NOW), inner


def test_a_valid_receipt_of_a_decision_to_pay_exactly_this_lets_the_payment_through() -> None:
    rail, inner = guarded()

    receipt = rail.execute(order(signed()))

    assert receipt.status == "simulated"
    assert len(inner.calls) == 1
    assert rail.name == "simulated"


def refused(payment: PaymentOrder) -> str:
    rail, inner = guarded()
    receipt = rail.execute(payment)
    assert inner.calls == [], "the rail was called"
    assert receipt.status == "failed"
    assert receipt.error is not None
    assert receipt.error.endswith("No se transfirió dinero.")
    return receipt.error


def test_no_receipt_no_payment() -> None:
    assert "no trae un recibo firmado" in refused(order(None))


def test_a_receipt_of_another_invoice_is_refused() -> None:
    other = body(invoice=body().invoice.model_copy(update={"id": "INV-0002"}))

    assert "otra factura" in refused(order(signed(other)))


def test_a_receipt_of_another_workspace_is_refused() -> None:
    assert "otra factura" in refused(order(signed(body(workspace_id="ws-otro"))))


def test_an_altered_receipt_is_refused_and_the_field_is_named() -> None:
    receipt = signed()
    assert receipt.body.payment is not None
    tampered = receipt.model_copy(
        update={
            "body": receipt.body.model_copy(
                update={"payment": receipt.body.payment.model_copy(update={"amount_base": "42000"})}
            )
        }
    )

    assert "monto en moneda base" in refused(order(tampered))


def test_a_receipt_signed_with_another_key_is_refused() -> None:
    stranger = other_signer()
    forged = sign_receipt(body(key_id=stranger.key_id), stranger)

    assert "no es válido" in refused(order(forged))


@pytest.mark.parametrize("verdict", ["hold", "escalate"])
def test_a_receipt_of_a_decision_that_was_not_to_pay_is_refused(verdict: str) -> None:
    held = sample_body(SIGNER.key_id, verdict="hold")
    held = held.model_copy(update={"decision": held.decision.model_copy(update={"verdict": verdict})})

    assert "no de pagar" in refused(order(signed(held)))


def test_a_different_amount_is_refused() -> None:
    assert "monto" in refused(replace(order(signed()), amount_base=Decimal("4200.01")))


def test_a_different_currency_or_invoiced_amount_is_refused() -> None:
    assert "monto" in refused(replace(order(signed()), amount=Decimal("4300")))
    assert "monto" in refused(replace(order(signed()), currency="COP"))


def test_a_different_beneficiary_is_refused() -> None:
    assert "beneficiario" in refused(replace(order(signed()), beneficiary_id="b-otro"))


def test_a_different_account_is_refused() -> None:
    swapped = ANDES.model_copy(update={"account_number": "999988887777"})

    assert "cuenta" in refused(replace(order(signed()), beneficiary=swapped))


def test_an_order_without_a_registered_account_is_refused() -> None:
    assert "cuenta" in refused(replace(order(signed()), beneficiary=None))
