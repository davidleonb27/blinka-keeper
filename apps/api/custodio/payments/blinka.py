"""Blinka, simulated: the exact instruction Custodio would hand Blinka, built and shown, never sent.

Blinka pays by ACH, wire, Bre-B (COP), SPEI (MXN) and Pix (BRL) but has no public API yet. So this rail stops one step
before the network: it picks Blinka's network for the payment, builds the instruction with the registered beneficiary's
bank details and returns it in the receipt with status "simulated". No money moves and nothing leaves Custodio.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from custodio.contracts import Beneficiary, PaymentInstruction, PaymentNetwork
from custodio.payments.port import BLINKA_SIMULATED, Clock, PaymentOrder, PaymentReceipt

USD = "USD"
DOMESTIC_COUNTRY = "US"  # ACH reaches US bank accounts only; a dollar payment anywhere else is a wire
WIRE_ABOVE_USD = Decimal("10000")  # above this, a same-day wire instead of a batched ACH
LOCAL_NETWORKS: Final[dict[str, PaymentNetwork]] = {"COP": "bre_b", "MXN": "spei", "BRL": "pix"}

NO_BENEFICIARY = (
    "El pago no tiene un beneficiario registrado con datos bancarios; no se armó ninguna instrucción para Blinka."
)
NO_AMOUNT = "El monto a pagar no es válido; no se armó ninguna instrucción para Blinka."
UNSUPPORTED_CURRENCY = (
    "Blinka no paga en {}: sólo USD (ACH o wire), COP (Bre-B), MXN (SPEI) y BRL (Pix). No se armó ninguna instrucción."
)


@dataclass(frozen=True)
class BlinkaRail:
    clock: Clock
    name: str = BLINKA_SIMULATED

    def execute(self, order: PaymentOrder) -> PaymentReceipt:
        beneficiary = order.beneficiary
        if order.beneficiary_id is None or beneficiary is None:
            return self._failed(NO_BENEFICIARY)
        if order.amount <= 0:
            return self._failed(NO_AMOUNT)
        currency = order.currency.strip().upper()
        network = network_for(currency, order.amount, beneficiary.country)
        if network is None:
            return self._failed(UNSUPPORTED_CURRENCY.format(currency))
        instruction = _instruction(order, beneficiary, network, currency)
        # The real call goes exactly here once Blinka delivers its API: POST `instruction` to Blinka's payments
        # endpoint with `instruction.idempotency_key` as its Idempotency-Key header and the company's Blinka key read
        # from an environment variable; then return Blinka's payment id as `external_id` and status "executed", or a
        # failed receipt with a Spanish message built from Blinka's error code (never its raw message). Until then
        # nothing is sent, and the receipt says so.
        return PaymentReceipt(
            rail=BLINKA_SIMULATED, status="simulated", executed_at=self.clock(), instruction=instruction
        )

    def _failed(self, message: str) -> PaymentReceipt:
        return PaymentReceipt(rail=BLINKA_SIMULATED, status="failed", executed_at=self.clock(), error=message)


def network_for(currency: str, amount: Decimal, country: str | None) -> PaymentNetwork | None:
    """Blinka's network for a payment, or None when Blinka does not pay in that currency."""
    if currency != USD:
        return LOCAL_NETWORKS.get(currency)
    if amount > WIRE_ABOVE_USD or country != DOMESTIC_COUNTRY:
        return "wire"
    return "ach"


def _instruction(
    order: PaymentOrder, beneficiary: Beneficiary, network: PaymentNetwork, currency: str
) -> PaymentInstruction:
    return PaymentInstruction(
        network=network,
        amount=order.amount,
        currency=currency,
        beneficiary_name=beneficiary.name,
        beneficiary_tax_id=beneficiary.tax_id,
        beneficiary_country=beneficiary.country,
        bank_name=beneficiary.bank_name,
        account_number=beneficiary.account_number,
        reference=order.acta_url,
        idempotency_key=order.idempotency_key,
    )
