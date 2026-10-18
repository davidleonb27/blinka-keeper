"""Custodio's payment record against Stripe's transfers: every recorded payment has exactly one transfer of the same
amount, and every transfer of the workspace has its recorded payment. Pure: no I/O, the same input gives the same lines.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from custodio.payments.stripe_lookup import StripeTransfer

LineKind = Literal["matched", "amount_differs", "missing_in_stripe", "missing_in_registry"]


@dataclass(frozen=True)
class RecordedPayment:
    invoice_id: str
    supplier_name: str | None
    amount_cents: int
    transfer_id: str


@dataclass(frozen=True)
class MatchLine:
    kind: LineKind
    invoice_id: str | None
    supplier_name: str | None
    recorded_cents: int | None
    stripe_cents: int | None
    transfer_id: str


@dataclass(frozen=True)
class RailMatch:
    lines: tuple[MatchLine, ...]
    recorded_cents: int
    stripe_cents: int

    @property
    def balanced(self) -> bool:
        return self.recorded_cents == self.stripe_cents and all(line.kind == "matched" for line in self.lines)


def settled_cents(transfer: StripeTransfer) -> int:
    """What the transfer still moves: a reversed part is money that came back."""
    return transfer.amount_cents - transfer.amount_reversed_cents


def match(workspace_id: str, recorded: Sequence[RecordedPayment], transfers: Sequence[StripeTransfer]) -> RailMatch:
    """Only transfers whose metadata names this workspace count; each one pairs with at most one recorded payment."""
    ours = {t.id: t for t in sorted(transfers, key=lambda t: t.id) if t.workspace_id == workspace_id}
    unused = dict(ours)
    lines = [_line(payment, unused.pop(payment.transfer_id, None)) for payment in sorted(recorded, key=_order)]
    lines += [_unrecorded(transfer) for transfer in unused.values()]
    return RailMatch(
        lines=tuple(lines),
        recorded_cents=sum(payment.amount_cents for payment in recorded),
        stripe_cents=sum(settled_cents(transfer) for transfer in ours.values()),
    )


def _line(payment: RecordedPayment, transfer: StripeTransfer | None) -> MatchLine:
    if transfer is None:
        kind: LineKind = "missing_in_stripe"
    elif settled_cents(transfer) == payment.amount_cents:
        kind = "matched"
    else:
        kind = "amount_differs"
    return MatchLine(
        kind=kind,
        invoice_id=payment.invoice_id,
        supplier_name=payment.supplier_name,
        recorded_cents=payment.amount_cents,
        stripe_cents=None if transfer is None else settled_cents(transfer),
        transfer_id=payment.transfer_id,
    )


def _unrecorded(transfer: StripeTransfer) -> MatchLine:
    return MatchLine(
        kind="missing_in_registry",
        invoice_id=transfer.invoice_id,
        supplier_name=None,
        recorded_cents=None,
        stripe_cents=settled_cents(transfer),
        transfer_id=transfer.id,
    )


def _order(payment: RecordedPayment) -> tuple[str, str]:
    return payment.invoice_id, payment.transfer_id
