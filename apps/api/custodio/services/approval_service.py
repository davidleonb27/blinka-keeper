"""Human approvals from the panel, Telegram or the API. Approving re-runs the engine at approval time, so an approval
never pays something a hold rule stops or that breaks the reserve."""

from __future__ import annotations

from typing import Literal

from custodio.contracts import Approval, Decision, DecisionStatus
from custodio.db.models import ApprovalRow, WorkspaceRow
from custodio.services import approval_tokens, invoice_service, records, workspace_service
from custodio.services.context import ServiceContext
from custodio.services.errors import DecisionNotPending

Channel = Literal["web", "telegram", "api"]


def decide(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    invoice_id: str,
    verdict: approval_tokens.Verdict,
    *,
    approver: str,
    channel: Channel,
    note: str | None = None,
) -> Decision:
    if records.decision(ctx, workspace.id, invoice_id).status is not DecisionStatus.PENDING_APPROVAL:
        raise DecisionNotPending()
    approval = Approval(
        invoice_id=invoice_id, decision=verdict, approver=approver, channel=channel, at=ctx.now(), note=note
    )
    ctx.session.add(
        ApprovalRow(
            workspace_id=workspace.id,
            invoice_id=invoice_id,
            decision=verdict,
            approver=approver,
            channel=channel,
            note=note,
            at=approval.at,
        )
    )
    approval_tokens.retire(ctx, workspace.id, invoice_id)
    invoice = records.invoice(ctx, workspace.id, invoice_id)
    outcome = invoice_service.decide(ctx, workspace, [invoice], approvals={invoice_id: approval})
    return outcome.batch.decisions[0]


def redeem_telegram(ctx: ServiceContext, token: str, chat_id: str) -> Decision:
    grant = approval_tokens.redeem(ctx, token, chat_id)
    workspace = workspace_service.get(ctx, grant.workspace_id)
    return decide(ctx, workspace, grant.invoice_id, grant.verdict, approver=grant.approver, channel="telegram")
