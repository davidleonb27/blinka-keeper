"""Earned autonomy: the auto-approval cap (R9) each supplier earns, folded from its trust history in the ledger.

The history is the supplier's `trust_raised` and `trust_revoked` entries; there is no counter kept anywhere else, so
the cap can always be recomputed from the chained ledger and checked. The fold, for one supplier:

- Without history the cap is the policy's `approval_threshold` (`start`): what Custodio did before earned autonomy.
- An incident (a risk signal: R2 hidden instructions, R4 changed account, R5 duplicate, R6 off the agreement, or a
  person rejecting a charge) sends the supplier back to supervised: cap = `floor`, streak and amounts reset.
- A clean payment (a person approved it and no risk signal fired) adds one to the streak. While the streak is under
  CLEAN_PAYMENTS_TO_EARN the earned cap is the floor; from then on it is the median of the approved amounts since the
  last incident times 1 + GROWTH_PER_PAYMENT for every clean payment past that mark, at most MAX_MULTIPLIER times.
- A clean payment never lowers the cap (it keeps the higher of the current and the earned one) and the cap never
  leaves [floor, ceiling]. The ceiling is `per_payment_limit`, or `approval_threshold` when the company makes it a
  hard ceiling.

Pure functions only: no I/O, no clock, no model.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum
from statistics import median

from custodio.contracts import Decision, DecisionStatus, LedgerEntry, LedgerKind, Policy, RuleOutcome, TrustCap
from custodio.engine.formatting import CENT, counted, money

CLEAN_PAYMENTS_TO_EARN = 3
GROWTH_PER_PAYMENT = Decimal("0.25")
MAX_MULTIPLIER = Decimal(2)
INCIDENT_RULES = ("R2", "R4", "R5", "R6")  # checked in this order; the first one failing names the incident
FAILED = (RuleOutcome.HOLD, RuleOutcome.ESCALATE)
CLEAN_REASON = "{approver} aprobó el pago y ninguna señal de riesgo se activó."
REJECTED_REASON = "{approver} rechazó el cobro {invoice_id}."


class TrustEventKind(StrEnum):
    CLEAN = "clean"
    INCIDENT = "incident"


@dataclass(frozen=True)
class TrustEvent:
    kind: TrustEventKind
    beneficiary_id: str
    invoice_id: str
    amount_base: Decimal | None  # set for a clean payment
    reason: str  # Spanish
    rule_id: str | None = None  # the rule that raised an incident; None for a rejection
    seq: int | None = None  # the ledger entry it was read from


@dataclass(frozen=True)
class TrustTerms:
    floor: Decimal
    ceiling: Decimal
    start: Decimal  # the cap of a supplier with no trust history
    base_currency: str


@dataclass(frozen=True)
class Envelope:
    cap: Decimal
    clean_streak: int
    supervised: bool
    amounts: tuple[Decimal, ...]  # approved amounts since the last incident
    last_incident: TrustEvent | None
    events: int  # how many events were folded; 0 means no history


@dataclass(frozen=True)
class NextStep:
    clean_needed: int  # clean payments until the cap changes
    cap: Decimal | None  # the cap then, if the next payments are of the median amount; None when nothing to go by


def terms_for(policy: Policy) -> TrustTerms:
    ceiling = policy.approval_threshold if policy.trust.hard_ceiling else policy.per_payment_limit
    floor = min(policy.trust.floor, ceiling)
    return TrustTerms(
        floor=floor,
        ceiling=ceiling,
        start=min(max(policy.approval_threshold, floor), ceiling),
        base_currency=policy.base_currency,
    )


def fold(events: Iterable[TrustEvent], terms: TrustTerms) -> Envelope:
    envelope = Envelope(terms.start, 0, supervised=False, amounts=(), last_incident=None, events=0)
    for event in events:
        envelope = step(envelope, event, terms)
    return envelope


def step(envelope: Envelope, event: TrustEvent, terms: TrustTerms) -> Envelope:
    if event.kind is TrustEventKind.INCIDENT:
        return Envelope(terms.floor, 0, supervised=True, amounts=(), last_incident=event, events=envelope.events + 1)
    streak = envelope.clean_streak + 1
    amounts = (*envelope.amounts, event.amount_base or Decimal(0))
    earned = earned_cap(streak, Decimal(median(amounts)), terms)
    return replace(
        envelope,
        cap=_bounded(max(envelope.cap, earned), terms),
        clean_streak=streak,
        supervised=envelope.supervised and streak < CLEAN_PAYMENTS_TO_EARN,
        amounts=amounts,
        events=envelope.events + 1,
    )


def earned_cap(streak: int, typical: Decimal, terms: TrustTerms) -> Decimal:
    """What `streak` clean payments around `typical` earn, before the ratchet and the bounds."""
    if streak < CLEAN_PAYMENTS_TO_EARN:
        return terms.floor
    multiplier = min(MAX_MULTIPLIER, 1 + GROWTH_PER_PAYMENT * (streak - CLEAN_PAYMENTS_TO_EARN))
    return _bounded((typical * multiplier).quantize(CENT, rounding=ROUND_DOWN), terms)


def next_step(envelope: Envelope, terms: TrustTerms) -> NextStep:
    needed = max(1, CLEAN_PAYMENTS_TO_EARN - envelope.clean_streak)
    if not envelope.amounts:
        return NextStep(needed, None)
    typical = Decimal(median(envelope.amounts))
    projected = envelope
    for _ in range(needed):
        projected = step(projected, TrustEvent(TrustEventKind.CLEAN, "", "", typical, ""), terms)
    return NextStep(needed, projected.cap)


def classify(decision: Decision) -> TrustEvent | None:
    """What a decision teaches about its supplier: an incident, a clean payment, or nothing."""
    supplier = decision.beneficiary_id
    if supplier is None:
        return None
    failing = {r.rule_id: r for r in decision.rules if r.outcome in FAILED}
    signal = next((failing[rule_id] for rule_id in INCIDENT_RULES if rule_id in failing), None)
    if signal is not None:
        return TrustEvent(
            TrustEventKind.INCIDENT, supplier, decision.invoice_id, None, signal.reason, rule_id=signal.rule_id
        )
    given = decision.approval
    if decision.status is DecisionStatus.REJECTED and given is not None:
        reason = REJECTED_REASON.format(approver=given.approver, invoice_id=decision.invoice_id)
        return TrustEvent(TrustEventKind.INCIDENT, supplier, decision.invoice_id, None, reason)
    if decision.status is DecisionStatus.PAID_HUMAN and given is not None and given.decision == "approved":
        reason = CLEAN_REASON.format(approver=given.approver)
        return TrustEvent(TrustEventKind.CLEAN, supplier, decision.invoice_id, decision.amount_base, reason)
    return None


def events_from_ledger(entries: Sequence[LedgerEntry]) -> dict[str, list[TrustEvent]]:
    """Every supplier's trust history, in ledger order."""
    history: defaultdict[str, list[TrustEvent]] = defaultdict(list)
    for entry in entries:
        kind = _KINDS.get(entry.kind)
        if kind is not None:
            event = _event(kind, entry.payload, entry.seq)
            history[event.beneficiary_id].append(event)
    return dict(history)


def trust_cap(envelope: Envelope, terms: TrustTerms, beneficiary_id: str) -> TrustCap:
    return TrustCap(
        beneficiary_id=beneficiary_id,
        cap=envelope.cap,
        clean_streak=envelope.clean_streak,
        supervised=envelope.supervised,
        reason=explain(envelope, terms),
    )


def explain(envelope: Envelope, terms: TrustTerms) -> str:
    cap, streak = money(envelope.cap, terms.base_currency), envelope.clean_streak
    if envelope.supervised:
        signal = envelope.last_incident.reason if envelope.last_incident else ""
        return (
            f"En supervisión tras una señal de riesgo: {signal} Lleva {streak} de {CLEAN_PAYMENTS_TO_EARN} pagos "
            f"limpios aprobados por una persona; mientras tanto su tope es {cap}."
        )
    if envelope.amounts and (envelope.cap > terms.start or envelope.last_incident is not None):
        typical = money(Decimal(median(envelope.amounts)), terms.base_currency)
        return (
            f"Tope ganado con {counted(streak, 'pago limpio seguido', 'pagos limpios seguidos')} aprobados por una "
            f"persona (mediana {typical}): {cap}."
        )
    return (
        f"{counted(streak, 'pago limpio', 'pagos limpios')} aprobados por una persona; el tope sigue en el de la "
        f"política, {cap}."
    )


def caps(history: Mapping[str, Sequence[TrustEvent]], terms: TrustTerms) -> dict[str, TrustCap]:
    """The cap the engine applies to every supplier with a trust history."""
    return {supplier: trust_cap(fold(events, terms), terms, supplier) for supplier, events in history.items()}


_KINDS = {LedgerKind.TRUST_RAISED: TrustEventKind.CLEAN, LedgerKind.TRUST_REVOKED: TrustEventKind.INCIDENT}


def _event(kind: TrustEventKind, payload: Mapping[str, object], seq: int) -> TrustEvent:
    amount = payload.get("amount_base")
    rule_id = payload.get("rule_id")
    return TrustEvent(
        kind=kind,
        beneficiary_id=str(payload["beneficiary_id"]),
        invoice_id=str(payload["invoice_id"]),
        amount_base=Decimal(str(amount)) if kind is TrustEventKind.CLEAN and amount is not None else None,
        reason=str(payload.get("reason", "")),
        rule_id=str(rule_id) if rule_id is not None else None,
        seq=seq,
    )


def _bounded(cap: Decimal, terms: TrustTerms) -> Decimal:
    return min(max(cap, terms.floor), terms.ceiling)
