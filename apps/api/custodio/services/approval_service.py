"""Human approvals from the acta in the panel. Approving re-runs the engine at approval time, so an approval never
pays something a hold rule stops or that breaks the reserve.

A person approves in one of two ways. «Sólo esta vez» pays this invoice and changes nothing else; the reason is
mandatory and stays in the ledger. «Aprobar y actualizar el acuerdo» also writes a new policy version with that
supplier's new agreement, after the person saw its simulation. Either way the decision is taken under the version in
force when it was given, and the ledger says which. Some rules no approval skips: a changed account, a duplicate,
instructions hidden in the document and a sanctions match are checked again at the moment of approving.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel

from custodio.contracts import Approval, Decision, PolicyChange, RuleOutcome, SimulationReport
from custodio.db.models import ApprovalRow, InvoiceRow, WorkspaceRow
from custodio.services import invoice_service, policy_service, records, trust_service
from custodio.services.agreements import AgreementUpdate, updated
from custodio.services.context import ServiceContext
from custodio.services.errors import ApprovalNotAllowed, DecisionNotPending, PolicyChanged

Verdict = Literal["approved", "rejected"]
CHANNEL: Final = "web"
HARD_RULES: Final = frozenset({"R2", "R4", "R5", "R14"})  # no approval skips them
FAILING: Final = frozenset({RuleOutcome.HOLD, RuleOutcome.ESCALATE})
HARD_RULE_REFUSAL: Final = "No se puede aprobar: {rules}. Estas reglas no se saltan con una aprobación; recházala."


class ApprovalMode(StrEnum):
    ONCE = "once"  # this invoice only; the policy stays as it is
    AGREEMENT_UPDATED = "agreement_updated"  # and the supplier's agreement changes from now on


class AgreementPreview(BaseModel):
    policy_version: int  # the version simulated; confirming against another one is refused
    changes: list[PolicyChange]
    simulation: SimulationReport


class ApprovedWithAgreement(BaseModel):
    decision: Decision
    policy_version: int  # the new version, with the updated agreement


def decide(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    invoice_id: str,
    verdict: Verdict,
    *,
    approver: str,
    note: str | None = None,
    mode: ApprovalMode | None = None,
    context: dict[str, object] | None = None,
) -> Decision:
    stored = records.decision(ctx, workspace.id, invoice_id)  # 404 when this workspace has no such decision
    invoice = records.invoice(ctx, workspace.id, invoice_id)
    if verdict == "approved":
        _refuse_hard_rules(ctx, workspace, stored, invoice)
    if not records.claim_pending(ctx, workspace.id, invoice_id):
        raise DecisionNotPending()
    approval = Approval(
        invoice_id=invoice_id, decision=verdict, approver=approver, channel=CHANNEL, at=ctx.now(), note=note
    )
    ctx.session.add(
        ApprovalRow(
            workspace_id=workspace.id,
            invoice_id=invoice_id,
            decision=verdict,
            approver=approver,
            channel=CHANNEL,
            note=note,
            at=approval.at,
        )
    )
    how = {"approval_mode": mode.value, **(context or {})} if mode else None
    outcome = invoice_service.decide(
        ctx, workspace, [invoice], approvals={invoice_id: approval}, execute_payments=True, approval_context=how
    )
    return outcome.batch.decisions[0]


def approve_once(
    ctx: ServiceContext, workspace: WorkspaceRow, invoice_id: str, *, approver: str, reason: str
) -> Decision:
    return decide(ctx, workspace, invoice_id, "approved", approver=approver, note=reason, mode=ApprovalMode.ONCE)


def preview_agreement(
    ctx: ServiceContext, workspace: WorkspaceRow, invoice_id: str, update: AgreementUpdate
) -> AgreementPreview:
    """What the new agreement would change across everything received, before anyone confirms it."""
    stored = records.decision(ctx, workspace.id, invoice_id)
    policy = policy_service.current(ctx, workspace.id)
    proposed, changes = updated(policy, stored.beneficiary_id, update, currency=stored.currency, quote="")
    simulation = policy_service.simulate(ctx, workspace, proposed)
    return AgreementPreview(policy_version=policy.version, changes=changes, simulation=simulation)


def approve_with_agreement(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    invoice_id: str,
    update: AgreementUpdate,
    *,
    approver: str,
    reason: str,
    simulated_on: int,
) -> ApprovedWithAgreement:
    """Approves under the version in force, then writes the next one with the new agreement."""
    stored = records.decision(ctx, workspace.id, invoice_id)
    policy = policy_service.current(ctx, workspace.id)
    proposed, _ = updated(policy, stored.beneficiary_id, update, currency=stored.currency, quote=reason)
    if policy.version != simulated_on:
        raise PolicyChanged()  # before approving: the person confirmed a simulation of another version
    next_version = policy.version + 1
    decision = decide(
        ctx,
        workspace,
        invoice_id,
        "approved",
        approver=approver,
        note=reason,
        mode=ApprovalMode.AGREEMENT_UPDATED,
        context={"agreement_policy_version": next_version},
    )
    context: dict[str, object] = {"author": approver, "reason": reason, "invoice_id": invoice_id}
    applied = policy_service.apply_reviewed(ctx, workspace.id, proposed, simulated_on=policy.version, context=context)
    return ApprovedWithAgreement(decision=decision, policy_version=applied.version)


def _refuse_hard_rules(ctx: ServiceContext, workspace: WorkspaceRow, stored: Decision, invoice: InvoiceRow) -> None:
    """Checks the hard rules on the stored acta and again on the invoice as it stands now."""
    policy = policy_service.current(ctx, workspace.id)
    state = trust_service.with_trust(ctx, workspace.id, records.company_state(ctx, workspace), policy)
    [now] = ctx.lanes.decide_all([records.as_case(invoice)], state, policy).decisions
    failing = {
        r.rule_id: r.label for d in (stored, now) for r in d.rules if r.rule_id in HARD_RULES and r.outcome in FAILING
    }
    if failing:
        rules = ", ".join(f"{rule_id} {label}" for rule_id, label in sorted(failing.items()))
        raise ApprovalNotAllowed(HARD_RULE_REFUSAL.format(rules=rules))
