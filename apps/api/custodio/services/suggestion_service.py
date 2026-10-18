"""«Keeper sugiere»: when people keep approving the same exception, propose the agreement change that would end it.

The evidence is the ledger's approval entries. Only R6 (a fixed agreement's tolerance, for one supplier) is ever
proposed: global caps (R9–R12) and the reserve stay as the policy says, and an approval that also failed a hard rule
(R2, R4, R5, R14) never counts. A proposal is shown with its simulation and applies only when a person accepts it.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from typing import Final

from pydantic import BaseModel

from custodio.contracts import (
    AgreementKind,
    Amount,
    Beneficiary,
    LedgerEntry,
    LedgerKind,
    Policy,
    PolicyChange,
    Ratio,
    SimulationReport,
)
from custodio.db.models import WorkspaceRow
from custodio.engine.formatting import money
from custodio.services import ledger_service, policy_service
from custodio.services.agreements import AgreementUpdate, effective_tolerance, updated
from custodio.services.approval_service import HARD_RULES
from custodio.services.context import ServiceContext
from custodio.services.errors import SuggestionNotFound

AGREEMENT_RULE: Final = "R6"
DEFAULT_MIN_APPROVALS: Final = 3
MAX_SUGGESTED_TOLERANCE_PCT: Final = Decimal(10)  # wider exceptions are a renegotiation, for a person to decide
HUNDRED: Final = Decimal(100)
ID_LENGTH: Final = 16


@dataclass(frozen=True)
class ApprovedException:
    invoice_id: str
    beneficiary_id: str
    amount: Decimal
    currency: str
    failed_rules: tuple[str, ...]
    approver: str
    approved_at: datetime
    note: str | None


class ApprovalEvidence(BaseModel):
    invoice_id: str
    amount: Amount
    currency: str
    deviation_pct: Ratio  # against the agreement as it stands now
    approver: str
    approved_at: datetime
    note: str | None


@dataclass(frozen=True)
class Proposal:
    id: str
    beneficiary: Beneficiary
    current_tolerance_pct: Decimal
    proposed_tolerance_pct: Decimal
    evidence: list[ApprovalEvidence]
    question: str
    proposed: Policy
    changes: list[PolicyChange]


class Suggestion(BaseModel):
    id: str
    beneficiary_id: str
    supplier_name: str
    rule_id: str
    question: str  # plain Spanish, with the evidence in numbers
    current_tolerance_pct: Ratio
    proposed_tolerance_pct: Ratio
    evidence: list[ApprovalEvidence]
    changes: list[PolicyChange]
    simulation: SimulationReport
    policy_version: int  # accepting against another version is refused


def propose(approvals: Sequence[ApprovedException], policy: Policy, *, min_approvals: int) -> list[Proposal]:
    """Pure: one proposal per supplier whose agreement exception was approved at least `min_approvals` times."""
    by_supplier: defaultdict[str, list[ApprovedException]] = defaultdict(list)
    for approval in approvals:
        if AGREEMENT_RULE in approval.failed_rules and not HARD_RULES & set(approval.failed_rules):
            by_supplier[approval.beneficiary_id].append(approval)
    suppliers = {b.id: b for b in policy.beneficiaries}
    proposals = (
        _proposal(suppliers[supplier], found, policy, min_approvals)
        for supplier, found in sorted(by_supplier.items())
        if supplier in suppliers
    )
    return [proposal for proposal in proposals if proposal is not None]


def suggestions(
    ctx: ServiceContext, workspace: WorkspaceRow, min_approvals: int = DEFAULT_MIN_APPROVALS
) -> list[Suggestion]:
    policy = policy_service.current(ctx, workspace.id)
    found = propose(_approved_exceptions(ctx, workspace.id), policy, min_approvals=min_approvals)
    return [
        _suggestion(proposal, policy_service.simulate(ctx, workspace, proposal.proposed), policy) for proposal in found
    ]


def accept(
    ctx: ServiceContext, workspace: WorkspaceRow, suggestion_id: str, *, approver: str, simulated_on: int
) -> Policy:
    """Applies a suggestion a person accepted: recomputed from the ledger here, never taken from the request, and only
    while its evidence still reaches the default threshold."""
    policy = policy_service.current(ctx, workspace.id)
    found = propose(_approved_exceptions(ctx, workspace.id), policy, min_approvals=DEFAULT_MIN_APPROVALS)
    proposal = next((p for p in found if p.id == suggestion_id), None)
    if proposal is None:
        raise SuggestionNotFound()
    context: dict[str, object] = {
        "author": approver,
        "reason": proposal.question,
        "suggestion_id": proposal.id,
        "evidence": [e.invoice_id for e in proposal.evidence],
    }
    return policy_service.apply_reviewed(
        ctx, workspace.id, proposal.proposed, simulated_on=simulated_on, context=context
    )


def _proposal(
    supplier: Beneficiary, approvals: list[ApprovedException], policy: Policy, min_approvals: int
) -> Proposal | None:
    deal = supplier.agreement
    if deal is None or deal.kind is not AgreementKind.FIXED or deal.amount <= 0:
        return None
    tolerance = effective_tolerance(deal, policy)
    evidence = sorted(
        (
            _evidence(a, (a.amount - deal.amount) * HUNDRED / deal.amount)
            for a in approvals
            if a.currency == deal.currency
        ),
        key=lambda e: (e.approved_at, e.invoice_id),
    )
    outside = [e for e in evidence if tolerance < abs(e.deviation_pct) <= MAX_SUGGESTED_TOLERANCE_PCT]
    if len(outside) < max(min_approvals, 1):
        return None
    proposed_tolerance = _covering(max(abs(e.deviation_pct) for e in outside))
    question = _question(supplier, outside, proposed_tolerance, deal.amount, deal.currency)
    proposed, changes = updated(
        policy, supplier.id, AgreementUpdate(tolerance_pct=proposed_tolerance), currency=deal.currency, quote=question
    )
    return Proposal(
        id=_id(supplier.id, proposed_tolerance, outside),
        beneficiary=supplier,
        current_tolerance_pct=tolerance,
        proposed_tolerance_pct=proposed_tolerance,
        evidence=outside,
        question=question,
        proposed=proposed,
        changes=changes,
    )


def _evidence(approval: ApprovedException, deviation: Decimal) -> ApprovalEvidence:
    return ApprovalEvidence(
        invoice_id=approval.invoice_id,
        amount=approval.amount,
        currency=approval.currency,
        deviation_pct=deviation.quantize(Decimal("0.01")),
        approver=approval.approver,
        approved_at=approval.approved_at,
        note=approval.note,
    )


def _covering(deviation: Decimal) -> Decimal:
    """The next whole percent above the widest approved deviation: 4.14 % → 5 %."""
    return min(deviation.to_integral_value(rounding=ROUND_FLOOR) + 1, MAX_SUGGESTED_TOLERANCE_PCT)


def _question(
    supplier: Beneficiary, evidence: list[ApprovalEvidence], tolerance: Decimal, agreed: Decimal, currency: str
) -> str:
    widest = max(abs(e.deviation_pct) for e in evidence)
    direction = "por encima" if any(e.deviation_pct > 0 for e in evidence) else "por debajo"
    return (
        f"Aprobaste {len(evidence)} veces a {supplier.name} por pasar hasta {_pct(widest)} {direction} del acuerdo "
        f"({money(agreed, currency)}); ¿subo la tolerancia de este proveedor a {_pct(tolerance)}?"
    )


def _pct(value: Decimal) -> str:
    text = f"{value.normalize():f}".replace(".", ",")
    return f"{text} %"


def _id(supplier_id: str, tolerance: Decimal, evidence: list[ApprovalEvidence]) -> str:
    seed = "|".join([supplier_id, AGREEMENT_RULE, str(tolerance), *sorted(e.invoice_id for e in evidence)])
    return hashlib.sha256(seed.encode()).hexdigest()[:ID_LENGTH]


def _suggestion(proposal: Proposal, simulation: SimulationReport, policy: Policy) -> Suggestion:
    return Suggestion(
        id=proposal.id,
        beneficiary_id=proposal.beneficiary.id,
        supplier_name=proposal.beneficiary.name,
        rule_id=AGREEMENT_RULE,
        question=proposal.question,
        current_tolerance_pct=proposal.current_tolerance_pct,
        proposed_tolerance_pct=proposal.proposed_tolerance_pct,
        evidence=proposal.evidence,
        changes=proposal.changes,
        simulation=simulation,
        policy_version=policy.version,
    )


def _approved_exceptions(ctx: ServiceContext, workspace_id: str) -> list[ApprovedException]:
    entries = ledger_service.entries(ctx, workspace_id, kinds=(LedgerKind.APPROVAL,))
    found = (_exception(entry) for entry in entries)
    return [approval for approval in found if approval is not None]


def _exception(entry: LedgerEntry) -> ApprovedException | None:
    """Approvals written before the payload carried the supplier and the amount have nothing to compare; skipped."""
    payload = entry.payload
    given = payload.get("approval") or {}
    if given.get("decision") != "approved" or not payload.get("beneficiary_id") or payload.get("amount") is None:
        return None
    return ApprovedException(
        invoice_id=str(entry.subject_id),
        beneficiary_id=str(payload["beneficiary_id"]),
        amount=Decimal(str(payload["amount"])),
        currency=str(payload.get("currency")),
        failed_rules=tuple(str(rule) for rule in payload.get("failed_rules", [])),
        approver=str(given.get("approver", "")),
        approved_at=datetime.fromisoformat(str(given.get("at"))),
        note=given.get("note"),
    )
