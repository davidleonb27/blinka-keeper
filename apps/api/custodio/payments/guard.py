"""The guard at the point of payment: defence in depth under the engine, the auditor and the attempts cap.

Every rail is wrapped in it. It sends nothing unless the order carries a receipt, signed with Blinka Keeper's key, of a
decision to pay exactly this invoice: the same workspace, amount, currency, beneficiary and registered account. Code
that skips the engine, or an order edited after the decision, meets a failed receipt and moves no money.
"""

from __future__ import annotations

from dataclasses import dataclass

from custodio.payments.port import Clock, PaymentOrder, PaymentRail, PaymentReceipt
from custodio.receipts import ReceiptPublicKey, account_fingerprint, amount_text, verify_receipt

REFUSED = "Guardián del pago: {} No se transfirió dinero."
NO_RECEIPT = "el pago no trae un recibo firmado de la decisión."
INVALID = "el recibo no es válido. {}"
NOT_PAY = "el recibo es de una decisión «{}», no de pagar."
OTHER_INVOICE = "el recibo es de otra factura."
OTHER_AMOUNT = "el monto del recibo ({} {}) no es el de la orden ({} {})."
OTHER_BENEFICIARY = "el beneficiario del recibo no es el de la orden."
OTHER_ACCOUNT = "la cuenta del recibo no es la cuenta registrada del beneficiario."


@dataclass(frozen=True)
class GuardedRail:
    inner: PaymentRail
    key: ReceiptPublicKey
    clock: Clock

    @property
    def name(self) -> str:
        return self.inner.name

    def execute(self, order: PaymentOrder) -> PaymentReceipt:
        reason = refusal(order, self.key)
        if reason is None:
            return self.inner.execute(order)
        return PaymentReceipt.model_validate(
            {"rail": self.inner.name, "status": "failed", "executed_at": self.clock(), "error": REFUSED.format(reason)}
        )


def refusal(order: PaymentOrder, key: ReceiptPublicKey) -> str | None:
    """Why this order must not be sent, or None when its receipt authorizes exactly it."""
    receipt = order.decision_receipt
    if receipt is None:
        return NO_RECEIPT
    check = verify_receipt(receipt.model_dump(mode="json"), key)
    if not check.valid:
        return INVALID.format(check.message)
    body = receipt.body
    if body.decision.verdict != "pay" or body.payment is None:
        return NOT_PAY.format(body.decision.verdict)
    if body.invoice.id != order.invoice_id or body.workspace_id != order.workspace_id:
        return OTHER_INVOICE
    payment = body.payment
    ordered = (amount_text(order.amount_base), amount_text(order.amount), order.currency)
    if (payment.amount_base, payment.amount, payment.currency) != ordered:
        return OTHER_AMOUNT.format(payment.amount, payment.currency, ordered[1], ordered[2])
    if payment.beneficiary_id != order.beneficiary_id:
        return OTHER_BENEFICIARY
    account = order.beneficiary.account_number if order.beneficiary else None
    if account is None or payment.account_sha256 != account_fingerprint(account):
        return OTHER_ACCOUNT
    return None
