"""One-time approval tokens for Telegram buttons.

Each pending decision sends its approvers two buttons (approve, reject). Each button carries a random token that is
stored only as its SHA-256, is bound to one chat, expires, and dies with its sibling the first time either is used.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from sqlalchemy import update

from custodio.contracts import Approver, Decision, Policy
from custodio.db.models import ApprovalTokenRow, WorkspaceRow
from custodio.services.context import ServiceContext
from custodio.services.errors import InvalidApprovalToken
from custodio.services.notifier import ApprovalRequest, NotificationFailed
from custodio.services.workspace_service import hash_secret

logger = logging.getLogger(__name__)

TOKEN_TTL = timedelta(hours=72)
TOKEN_BYTES = 24  # 32 url-safe characters: inside Telegram's 64-byte callback_data limit

Verdict = Literal["approved", "rejected"]


@dataclass(frozen=True)
class TokenGrant:
    workspace_id: str
    invoice_id: str
    verdict: Verdict
    approver: str


def request_approvals(
    ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy, pending: Sequence[Decision]
) -> None:
    reachable = [approver for approver in policy.approvers if approver.telegram_chat_id]
    for decision in pending:
        for approver in reachable:
            _send(ctx, workspace, decision, approver)


def redeem(ctx: ServiceContext, token: str, chat_id: str) -> TokenGrant:
    row = ctx.session.get(ApprovalTokenRow, hash_secret(token))
    if row is None or row.used_at is not None or row.expires_at <= ctx.now() or row.chat_id != chat_id:
        raise InvalidApprovalToken()
    retire(ctx, row.workspace_id, row.invoice_id)
    verdict: Verdict = "approved" if row.action == "approved" else "rejected"
    return TokenGrant(workspace_id=row.workspace_id, invoice_id=row.invoice_id, verdict=verdict, approver=row.approver)


def retire(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> None:
    ctx.session.execute(
        update(ApprovalTokenRow)
        .where(
            ApprovalTokenRow.workspace_id == workspace_id,
            ApprovalTokenRow.invoice_id == invoice_id,
            ApprovalTokenRow.used_at.is_(None),
        )
        .values(used_at=ctx.now())
    )


def _send(ctx: ServiceContext, workspace: WorkspaceRow, decision: Decision, approver: Approver) -> None:
    chat_id = approver.telegram_chat_id or ""
    request = ApprovalRequest(
        chat_id=chat_id,
        text=_summary(workspace.company_name, decision),
        approve_token=_issue(ctx, workspace.id, decision.invoice_id, approver, chat_id, "approved"),
        reject_token=_issue(ctx, workspace.id, decision.invoice_id, approver, chat_id, "rejected"),
    )
    try:
        ctx.runtime.notifier.send_approval_request(request)
    except NotificationFailed as error:
        logger.warning("approval request not delivered for %s: %s", decision.invoice_id, error)


def _issue(
    ctx: ServiceContext, workspace_id: str, invoice_id: str, approver: Approver, chat_id: str, action: Verdict
) -> str:
    token = secrets.token_urlsafe(TOKEN_BYTES)
    ctx.session.add(
        ApprovalTokenRow(
            token_hash=hash_secret(token),
            workspace_id=workspace_id,
            invoice_id=invoice_id,
            action=action,
            approver=approver.name,
            chat_id=chat_id,
            expires_at=ctx.now() + TOKEN_TTL,
            used_at=None,
        )
    )
    return token


def _summary(company_name: str, decision: Decision) -> str:
    amount = f"{decision.currency or ''} {decision.amount}" if decision.amount is not None else "monto no leído"
    return (
        f"Custodio necesita tu aprobación · {company_name}\n"
        f"Factura {decision.invoice_id} de {decision.supplier_name or 'proveedor no leído'}: {amount}\n"
        f"{decision.explanation}"
    )
