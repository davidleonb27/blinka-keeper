"""Past approvals of the demo company, so «Custodio sugiere» has real history to learn from.

Ana approved Nube Austral SpA (b8, a fixed 2,150 USD hosting agreement with the policy's 2 % tolerance) three times
this year at about 4 % above the agreement, each time «sólo esta vez» and with her reason. They predate the demo's
September history, so no rule of the current batch (duplicates, splits, the month's cupo) sees them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class SeededApproval:
    invoice_id: str
    invoice_number: str
    beneficiary_id: str
    amount: Decimal
    currency: str
    approved_on: date
    approver: str
    reason: str
    failed_rules: tuple[str, ...] = ("R6",)

    @property
    def approved_at(self) -> datetime:
        return datetime(self.approved_on.year, self.approved_on.month, self.approved_on.day, 15, tzinfo=UTC)


DEMO_APPROVALS = (
    SeededApproval(
        invoice_id="H-NA-7712",
        invoice_number="NA-7712",
        beneficiary_id="b8",
        amount=Decimal("2236.00"),
        currency="USD",
        approved_on=date(2026, 6, 5),
        approver="Ana Gómez",
        reason="Nube Austral subió el plan de hosting; lo confirmé con su contacto registrado.",
    ),
    SeededApproval(
        invoice_id="H-NA-7735",
        invoice_number="NA-7735",
        beneficiary_id="b8",
        amount=Decimal("2232.00"),
        currency="USD",
        approved_on=date(2026, 7, 3),
        approver="Ana Gómez",
        reason="Mismo plan nuevo de hosting; el contrato aún no se actualiza.",
    ),
    SeededApproval(
        invoice_id="H-NA-7758",
        invoice_number="NA-7758",
        beneficiary_id="b8",
        amount=Decimal("2239.00"),
        currency="USD",
        approved_on=date(2026, 8, 4),
        approver="Ana Gómez",
        reason="Plan nuevo de hosting más un ajuste por tráfico; aprobado sólo esta vez.",
    ),
)
