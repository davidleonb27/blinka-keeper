"""The month in figures: what Blinka Keeper decided and what the bank confirmed. Pure."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal

from custodio.contracts import Decision, DecisionStatus
from custodio.reconciliation.models import (
    NEEDS_REVIEW,
    MovementResult,
    MovementStatus,
    PaymentStatus,
    PeriodSummary,
    ReconciliationOutcome,
    Review,
    Statement,
    Tally,
)

RECONCILED = frozenset({MovementStatus.RECONCILED, MovementStatus.RECONCILED_WITH_DIFFERENCE})
UNEXPLAINED = frozenset({MovementStatus.UNMATCHED_OUTFLOW, MovementStatus.DUPLICATE})
CENT = Decimal("0.01")


def summarize(
    decisions: Sequence[Decision],
    statement: Statement,
    outcome: ReconciliationOutcome,
    reviews: Sequence[Review],
    *,
    currency: str,
) -> PeriodSummary:
    amounts = {m.id: abs(m.amount) if m.amount is not None else Decimal(0) for m in statement.movements}
    reviewed = {review.movement_id for review in reviews}
    by_status = _grouped(outcome)
    alerts = [item.movement_id for item in outcome.movements if item.status in NEEDS_REVIEW]
    with_difference = [payment.difference for payment in outcome.payments if payment.difference is not None]
    pending = [payment for payment in outcome.payments if payment.status is PaymentStatus.PENDING]
    return PeriodSummary(
        currency=currency,
        paid=_decided(decisions, DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN),
        held=_decided(decisions, DecisionStatus.HOLD),
        rejected=_decided(decisions, DecisionStatus.REJECTED),
        pending_approval=_decided(decisions, DecisionStatus.PENDING_APPROVAL),
        reconciled=_tally(item.allocated for status in RECONCILED for item in by_status.get(status, [])),
        differences=_tally(with_difference),
        fees=_tally(amounts[item.movement_id] for item in by_status.get(MovementStatus.BANK_FEE, [])),
        inflows=_tally(amounts[item.movement_id] for item in by_status.get(MovementStatus.INFLOW, [])),
        unexplained=_tally(amounts[item.movement_id] for status in UNEXPLAINED for item in by_status.get(status, [])),
        pending_in_bank=_tally(payment.expected or Decimal(0) for payment in pending),
        alerts=len(alerts),
        alerts_open=sum(movement_id not in reviewed for movement_id in alerts),
    )


def _grouped(outcome: ReconciliationOutcome) -> dict[MovementStatus, list[MovementResult]]:
    grouped: dict[MovementStatus, list[MovementResult]] = {}
    for item in outcome.movements:
        grouped.setdefault(item.status, []).append(item)
    return grouped


def _decided(decisions: Sequence[Decision], *statuses: DecisionStatus) -> Tally:
    return _tally(decision.amount_base or Decimal(0) for decision in decisions if decision.status in statuses)


def _tally(amounts: Iterable[Decimal]) -> Tally:
    values = list(amounts)
    return Tally(count=len(values), total=sum(values, Decimal(0)).quantize(CENT, rounding=ROUND_HALF_UP))
