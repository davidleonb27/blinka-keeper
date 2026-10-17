"""Earned autonomy, stored where everything else is: the chained ledger.

Each decision that says something about a supplier (a risk signal, a rejection, or a payment a person approved without
one) appends a `trust_revoked` or `trust_raised` entry. The caps are folded back from those entries every time, so
there is no counter to drift from the ledger. The fold and its formula are custodio.engine.trust.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from custodio.contracts import Amount, CompanyState, Decision, LedgerEntry, LedgerKind, Policy
from custodio.db.models import WorkspaceRow
from custodio.engine.formatting import money
from custodio.engine.trust import (
    CLEAN_PAYMENTS_TO_EARN,
    Envelope,
    TrustEvent,
    TrustEventKind,
    TrustTerms,
    caps,
    classify,
    events_from_ledger,
    explain,
    fold,
    next_step,
    step,
    terms_for,
)
from custodio.services import ledger_service, policy_service, records
from custodio.services.context import ServiceContext

TRUST_KINDS = (LedgerKind.TRUST_RAISED, LedgerKind.TRUST_REVOKED)
NO_HISTORY = "Sin historial de confianza: usa el tope de aprobación automática de la política, {cap}."


class TrustStep(BaseModel):
    """One entry of a supplier's trust history, as the ledger holds it."""

    seq: int
    at: datetime
    kind: Literal["trust_raised", "trust_revoked"]
    invoice_id: str
    rule_id: str | None
    reason: str  # why it happened
    summary: str  # where it left the supplier
    cap_before: Amount | None
    cap_after: Amount | None
    clean_streak: int | None
    hash: str


class SupplierTrust(BaseModel):
    beneficiary_id: str
    supplier_name: str
    has_history: bool
    cap: Amount
    clean_streak: int
    supervised: bool
    reason: str
    clean_needed: int  # clean payments until the cap moves
    next_cap: Amount | None  # the cap after them, if they are of the median amount; None with nothing to go by
    last_incident: TrustStep | None
    timeline: list[TrustStep]


class AutonomyDay(BaseModel):
    day: date  # the day the invoices arrived
    decisions: int
    decided_alone: int  # paid or held by the agent without a person
    rate: float


class TrustOverview(BaseModel):
    base_currency: str
    autonomy_rate: float
    floor: Amount
    ceiling: Amount
    policy_threshold: Amount
    hard_ceiling: bool
    clean_payments_to_earn: int
    suppliers: list[SupplierTrust]
    autonomy: list[AutonomyDay]


def with_trust(ctx: ServiceContext, workspace_id: str, state: CompanyState, policy: Policy) -> CompanyState:
    """The company state with the cap each supplier with a trust history has earned."""
    return state.model_copy(update={"trust": caps(_history(ctx, workspace_id), terms_for(policy))})


def learn(ctx: ServiceContext, workspace_id: str, decision: Decision, policy: Policy) -> LedgerEntry | None:
    """Appends what this decision teaches about its supplier, once per invoice and kind."""
    event = classify(decision)
    if event is None:
        return None
    earlier = _history(ctx, workspace_id).get(event.beneficiary_id, [])
    if any(e.invoice_id == event.invoice_id and e.kind is event.kind for e in earlier):
        return None
    terms = terms_for(policy)
    before = fold(earlier, terms)
    after = step(before, event, terms)
    kind = LedgerKind.TRUST_RAISED if event.kind is TrustEventKind.CLEAN else LedgerKind.TRUST_REVOKED
    return ledger_service.append(ctx, workspace_id, kind, event.beneficiary_id, _payload(event, before, after, terms))


def overview(ctx: ServiceContext, workspace: WorkspaceRow) -> TrustOverview:
    policy = policy_service.current(ctx, workspace.id)
    terms = terms_for(policy)
    entries = _entries(ctx, workspace.id)
    history = events_from_ledger(entries)
    steps = _steps(entries)
    names = {b.id: b.name for b in policy.beneficiaries if b.allowed}
    ordered = sorted({*names, *history}, key=lambda supplier: (supplier not in history, names.get(supplier, supplier)))
    return TrustOverview(
        base_currency=policy.base_currency,
        autonomy_rate=records.metrics(ctx, workspace.id).autonomy_rate,
        floor=terms.floor,
        ceiling=terms.ceiling,
        policy_threshold=policy.approval_threshold,
        hard_ceiling=policy.trust.hard_ceiling,
        clean_payments_to_earn=CLEAN_PAYMENTS_TO_EARN,
        suppliers=[_supplier(s, names.get(s, s), history.get(s, []), steps.get(s, []), terms) for s in ordered],
        autonomy=_autonomy(ctx, workspace.id),
    )


def _supplier(
    supplier: str, name: str, events: list[TrustEvent], timeline: list[TrustStep], terms: TrustTerms
) -> SupplierTrust:
    envelope = fold(events, terms)
    ahead = next_step(envelope, terms)
    incidents = [entry for entry in timeline if entry.kind == "trust_revoked"]
    return SupplierTrust(
        beneficiary_id=supplier,
        supplier_name=name,
        has_history=bool(events),
        cap=envelope.cap,
        clean_streak=envelope.clean_streak,
        supervised=envelope.supervised,
        reason=explain(envelope, terms) if events else NO_HISTORY.format(cap=money(terms.start, terms.base_currency)),
        clean_needed=ahead.clean_needed,
        next_cap=ahead.cap,
        last_incident=incidents[-1] if incidents else None,
        timeline=timeline,
    )


def _autonomy(ctx: ServiceContext, workspace_id: str) -> list[AutonomyDay]:
    days: defaultdict[date, list[bool]] = defaultdict(list)
    for decided, invoice in records.decisions(ctx, workspace_id):
        days[invoice.received_at.date()].append(decided.status in records.AUTONOMOUS)
    return [
        AutonomyDay(day=day, decisions=len(alone), decided_alone=sum(alone), rate=sum(alone) / len(alone))
        for day, alone in sorted(days.items())
    ]


def _history(ctx: ServiceContext, workspace_id: str) -> dict[str, list[TrustEvent]]:
    return events_from_ledger(_entries(ctx, workspace_id))


def _entries(ctx: ServiceContext, workspace_id: str) -> list[LedgerEntry]:
    return ledger_service.entries(ctx, workspace_id, kinds=TRUST_KINDS)


def _steps(entries: list[LedgerEntry]) -> dict[str, list[TrustStep]]:
    steps: defaultdict[str, list[TrustStep]] = defaultdict(list)
    for entry in entries:
        payload = entry.payload
        steps[str(payload["beneficiary_id"])].append(
            TrustStep(
                seq=entry.seq,
                at=entry.at,
                kind="trust_raised" if entry.kind is LedgerKind.TRUST_RAISED else "trust_revoked",
                invoice_id=str(payload["invoice_id"]),
                rule_id=payload.get("rule_id"),
                reason=str(payload.get("reason", "")),
                summary=str(payload.get("summary", "")),
                cap_before=_amount(payload.get("cap_before")),
                cap_after=_amount(payload.get("cap_after")),
                clean_streak=payload.get("clean_streak"),
                hash=entry.hash,
            )
        )
    return dict(steps)


def _payload(event: TrustEvent, before: Envelope, after: Envelope, terms: TrustTerms) -> dict[str, object]:
    """Plain JSON values only, as every ledger payload."""
    return {
        "beneficiary_id": event.beneficiary_id,
        "invoice_id": event.invoice_id,
        "amount_base": None if event.amount_base is None else str(event.amount_base),
        "rule_id": event.rule_id,
        "reason": event.reason,
        "summary": explain(after, terms),
        "cap_before": str(before.cap),
        "cap_after": str(after.cap),
        "clean_streak": after.clean_streak,
    }


def _amount(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))
