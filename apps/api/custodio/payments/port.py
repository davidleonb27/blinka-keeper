"""The seam between deciding a payment and sending it.

The engine and the auditor decide; a rail only carries out what they already decided. Swapping the rail (simulated,
Stripe in test mode, the company's own bank rail) never changes a rule or who decides.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final, Literal, Protocol

from sqlalchemy.orm import Session

from custodio.contracts import PaymentExecution

RailName = Literal["simulated", "stripe_test"]
SIMULATED: Final = "simulated"
STRIPE_TEST: Final = "stripe_test"

# The rail's answer is exactly what the acta shows, so the receipt and the contract are one model.
PaymentReceipt = PaymentExecution
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class PaymentOrder:
    idempotency_key: str
    workspace_id: str
    invoice_id: str
    beneficiary_id: str | None
    supplier_name: str
    amount_base: Decimal  # USD, what the rail sends
    currency: str  # as invoiced
    amount: Decimal  # as invoiced
    acta_url: str


class PaymentRail(Protocol):
    @property
    def name(self) -> str: ...

    def execute(self, order: PaymentOrder) -> PaymentReceipt: ...


@dataclass(frozen=True)
class RailChoice:
    """The rail this deployment pays with, built per unit of work so it can keep its own records in that session."""

    name: RailName
    build: Callable[[Session, Clock], PaymentRail]
