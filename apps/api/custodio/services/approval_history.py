"""Seeds the demo company's past approvals into its ledger and payment history (see custodio.dataset.approvals).

They are written exactly as a live «Aprobar sólo esta vez» writes them, marked `seeded`, so «Keeper sugiere» reads
them through the same path as any other approval.
"""

from __future__ import annotations

from decimal import Decimal

from custodio.contracts import AgentVerdict, Approval, DecisionStatus, LedgerKind, PaymentRecord, Policy
from custodio.dataset import DEMO_APPROVALS, SeededApproval
from custodio.db.models import WorkspaceRow
from custodio.services import ledger_service
from custodio.services.context import ServiceContext

ONCE = "once"


def seed_demo(ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy) -> None:
    """Only approvals of suppliers this company has, in their agreement's currency."""
    fx = {currency: Decimal(units) for currency, units in workspace.fx_units_per_base.items()}
    deals = {b.id: b.agreement for b in policy.beneficiaries if b.agreement is not None}
    seeded = [a for a in DEMO_APPROVALS if a.beneficiary_id in deals and deals[a.beneficiary_id].currency == a.currency]
    seeded = [a for a in seeded if a.currency in fx]
    for approval in seeded:
        amount_base = (approval.amount / fx[approval.currency]).quantize(Decimal("0.01"))
        payload = _payload(approval, amount_base, policy.version)
        ledger_service.append(ctx, workspace.id, LedgerKind.APPROVAL, approval.invoice_id, payload)
    workspace.history_seed = [*workspace.history_seed, *(_paid(a, fx).model_dump(mode="json") for a in seeded)]


def _payload(approval: SeededApproval, amount_base: Decimal, policy_version: int) -> dict[str, object]:
    given = Approval(
        invoice_id=approval.invoice_id,
        decision="approved",
        approver=approval.approver,
        channel="web",
        at=approval.approved_at,
        note=approval.reason,
    )
    return {
        "status": DecisionStatus.PAID_HUMAN.value,
        "agent_verdict": AgentVerdict.ESCALATE.value,
        "amount_base": str(amount_base),
        "failed_rules": list(approval.failed_rules),
        "audit_blocked": False,
        "beneficiary_id": approval.beneficiary_id,
        "amount": str(approval.amount),
        "currency": approval.currency,
        "invoice_number": approval.invoice_number,
        "policy_version": policy_version,
        "approval_mode": ONCE,
        "seeded": True,
        "approval": given.model_dump(mode="json"),
    }


def _paid(approval: SeededApproval, fx: dict[str, Decimal]) -> PaymentRecord:
    return PaymentRecord(
        invoice_id=approval.invoice_id,
        beneficiary_id=approval.beneficiary_id,
        invoice_number=approval.invoice_number,
        amount=approval.amount,
        currency=approval.currency,
        amount_base=approval.amount / fx[approval.currency],
        paid_on=approval.approved_on,
        by="person",
    )
