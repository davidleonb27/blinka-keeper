"""Human approvals from the panel, Telegram or the API. Approving re-runs the engine at approval time, so an approval
never pays something a hold rule stops or that breaks the reserve."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from custodio.contracts import Approval, Decision, DecisionStatus
from custodio.db.models import ApprovalRow, WorkspaceRow
from custodio.services import approval_tokens, invoice_service, records, workspace_service
from custodio.services.context import ServiceContext
from custodio.services.errors import DecisionNotPending, InvalidApprovalToken
from custodio.services.notifier import NotificationFailed

logger = logging.getLogger(__name__)

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


STATUS_WORDS = {
    DecisionStatus.PAID_HUMAN: "aprobada y pagada",
    DecisionStatus.PAID_AUTO: "pagada",
    DecisionStatus.REJECTED: "rechazada",
    DecisionStatus.HOLD: "retenida: no se pagó",
    DecisionStatus.PENDING_APPROVAL: "sigue pendiente",
}


@dataclass(frozen=True)
class ButtonOutcome:
    handled: bool
    message: str
    status: DecisionStatus | None = None


def press_button(ctx: ServiceContext, *, callback_id: str, token: str, chat_id: str) -> ButtonOutcome:
    """A Telegram button press. Always answered, so the approver sees what happened, even for a dead button."""
    try:
        decision = redeem_telegram(ctx, token, chat_id)
    except (InvalidApprovalToken, DecisionNotPending) as error:
        outcome = ButtonOutcome(handled=False, message=error.message)
    else:
        message = f"Factura {decision.invoice_id} {STATUS_WORDS[decision.status]}."
        outcome = ButtonOutcome(handled=True, message=message, status=decision.status)
    try:
        ctx.runtime.notifier.answer_callback(callback_id, outcome.message)
    except NotificationFailed as error:
        logger.warning("telegram callback not answered: %s", error)
    return outcome
