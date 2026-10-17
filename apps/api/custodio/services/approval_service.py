"""Human approvals from the acta in the panel. Approving re-runs the engine at approval time, so an approval never
pays something a hold rule stops or that breaks the reserve."""

from __future__ import annotations

from typing import Final, Literal

from custodio.contracts import Approval, Decision, DecisionStatus
from custodio.db.models import ApprovalRow, WorkspaceRow
from custodio.services import invoice_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import DecisionNotPending

Verdict = Literal["approved", "rejected"]
CHANNEL: Final = "web"


def decide(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    invoice_id: str,
    verdict: Verdict,
    *,
    approver: str,
    note: str | None = None,
) -> Decision:
    if records.decision(ctx, workspace.id, invoice_id).status is not DecisionStatus.PENDING_APPROVAL:
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
    invoice = records.invoice(ctx, workspace.id, invoice_id)
    outcome = invoice_service.decide(ctx, workspace, [invoice], approvals={invoice_id: approval})
    return outcome.batch.decisions[0]
