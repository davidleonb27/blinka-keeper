"""Carrying out what the engine and the auditor already decided, through the deployment's payment rail.

Only a visitor's own workspace executes, and only from the panel (processing and approvals): the firewall answers
another agent, who pays; the challenge and the red team are sandboxes. One execution per invoice: an executed or
simulated one is reused and the rail is never called again; a failed one can be retried as a new attempt.
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select

from custodio.contracts import Beneficiary, Decision, DecisionStatus, LedgerKind, PaymentExecution, Policy
from custodio.db.models import PaymentExecutionRow, WorkspaceRow
from custodio.payments import MOVES_NO_MONEY, PaymentOrder, PaymentRail, PaymentReceipt
from custodio.receipts import DecisionReceipt
from custodio.services import ledger_service, policy_service, receipt_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import DecisionNotFound, PaymentNotRetryable, ReceiptUnavailable
from custodio.services.workspace_service import VISITOR_KINDS

SETTLED = frozenset({"executed", "simulated"})
RAIL_CURRENCY = "USD"
CAP_REACHED = "Tope de pagos de prueba alcanzado"
WORKSPACE_CAP = CAP_REACHED + ": {} transferencias en este espacio. No se transfirió dinero."
DAILY_CAP = CAP_REACHED + ": {} transferencias hoy (UTC) en todo Custodio. No se transfirió dinero; reintenta mañana."
NOT_USD = "El riel de prueba sólo paga en USD y la moneda base de este espacio es {}. No se transfirió dinero."
NO_ATTEMPTS_LEFT = "Este pago ya usó el máximo de {} intentos. No se transfirió dinero."


def may_execute(workspace: WorkspaceRow) -> bool:
    return workspace.kind in VISITOR_KINDS


def execute(ctx: ServiceContext, workspace_id: str, decision: Decision, policy: Policy) -> PaymentExecution:
    row = _row(ctx, workspace_id, decision.invoice_id)
    if row is not None and row.status in SETTLED:
        return _execution(row)
    attempt = 1 if row is None else row.attempts + 1
    rail = ctx.payment_rail()
    receipt = _refusal(ctx, workspace_id, rail, policy, attempt) or rail.execute(
        _order(ctx, workspace_id, decision, policy, attempt)
    )
    _store(ctx, workspace_id, decision.invoice_id, receipt, attempt, row)
    return receipt


def retry(ctx: ServiceContext, workspace: WorkspaceRow, invoice_id: str) -> Decision:
    """Idempotent: a payment that already went out is returned as is; only a failed execution is sent again."""
    decision = records.decision(ctx, workspace.id, invoice_id)
    if decision.execution is None or decision.status not in records.PAID or not may_execute(workspace):
        raise PaymentNotRetryable()
    if decision.execution.status in SETTLED:
        return decision
    execution = execute(ctx, workspace.id, decision, policy_service.current(ctx, workspace.id))
    retried = decision.model_copy(update={"execution": execution})
    records.attach_execution(ctx, workspace.id, retried)
    ledger_service.append(
        ctx, workspace.id, LedgerKind.PAYMENT, invoice_id, {**payment_payload(retried), "retry": True}
    )
    return retried


def payment_payload(decision: Decision) -> dict[str, Any]:
    execution = decision.execution
    return {
        "beneficiary_id": decision.beneficiary_id,
        "amount": _number(decision.amount),
        "currency": decision.currency,
        "amount_base": _number(decision.amount_base),
        "by": "person" if decision.status is DecisionStatus.PAID_HUMAN else "agent",
        "rail": execution.rail if execution else None,
        "execution_status": execution.status if execution else None,
        "external_id": execution.external_id if execution else None,
        "livemode": False,
    }


def _refusal(
    ctx: ServiceContext, workspace_id: str, rail: PaymentRail, policy: Policy, attempt: int
) -> PaymentReceipt | None:
    """Why the rail must not be called for this payment, as the failed receipt the acta shows.

    Every rail has the attempts cap, since a rail that moves no money can still refuse the same payment on every
    click; the transfer caps and the USD base only bind the rails that move money.
    """
    allowed = ctx.runtime.limits.payment_attempts_per_invoice
    if attempt > allowed:
        reason: str | None = NO_ATTEMPTS_LEFT.format(allowed)
    elif rail.name in MOVES_NO_MONEY:
        return None
    else:
        reason = _cap_reached(ctx, workspace_id, rail.name)
    if reason is None and policy.base_currency != RAIL_CURRENCY:
        reason = NOT_USD.format(policy.base_currency)
    if reason is None:
        return None
    return PaymentReceipt(rail=rail.name, status="failed", executed_at=ctx.now(), error=reason)


def _cap_reached(ctx: ServiceContext, workspace_id: str, rail_name: str) -> str | None:
    limits = ctx.runtime.limits
    executed = (
        select(func.count())
        .select_from(PaymentExecutionRow)
        .where(PaymentExecutionRow.rail == rail_name, PaymentExecutionRow.status == "executed")
    )
    if (ctx.session.scalar(executed.where(PaymentExecutionRow.workspace_id == workspace_id)) or 0) >= (
        limits.test_transfers_per_workspace
    ):
        return WORKSPACE_CAP.format(limits.test_transfers_per_workspace)
    today = datetime.combine(ctx.now().astimezone(UTC).date(), time.min, tzinfo=UTC)
    if (ctx.session.scalar(executed.where(PaymentExecutionRow.executed_at >= today)) or 0) >= (
        limits.test_transfers_per_day
    ):
        return DAILY_CAP.format(limits.test_transfers_per_day)
    return None


def _order(ctx: ServiceContext, workspace_id: str, decision: Decision, policy: Policy, attempt: int) -> PaymentOrder:
    # Stripe replays the stored answer of a used key, errors included, so each new attempt carries its own key.
    key = f"{workspace_id}:{decision.invoice_id}"
    amount_base = decision.amount_base or Decimal(0)
    return PaymentOrder(
        idempotency_key=key if attempt == 1 else f"{key}:intento-{attempt}",
        workspace_id=workspace_id,
        invoice_id=decision.invoice_id,
        beneficiary_id=decision.beneficiary_id,
        supplier_name=_beneficiary_name(decision, policy),
        amount_base=amount_base,
        currency=decision.currency or RAIL_CURRENCY,
        amount=decision.amount if decision.amount is not None else amount_base,
        acta_url=records.acta_url(ctx.runtime.public_base_url, decision.invoice_id),
        beneficiary=_registered(decision, policy),
        decision_receipt=_receipt(ctx, workspace_id, decision, policy),
    )


def _receipt(ctx: ServiceContext, workspace_id: str, decision: Decision, policy: Policy) -> DecisionReceipt | None:
    """None when the ledger does not show this decision: the rail's guard then refuses the order."""
    try:
        return receipt_service.issue(ctx, workspace_id, decision, policy)
    except (ReceiptUnavailable, DecisionNotFound):
        return None


def _registered(decision: Decision, policy: Policy) -> Beneficiary | None:
    return next((b for b in policy.beneficiaries if b.id == decision.beneficiary_id), None)


def _beneficiary_name(decision: Decision, policy: Policy) -> str:
    """The registered name, not the invoice's spelling, so every invoice of a supplier reaches the same account."""
    registered = _registered(decision, policy)
    return registered.name if registered else decision.supplier_name or ""


def _row(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> PaymentExecutionRow | None:
    return ctx.session.scalars(
        select(PaymentExecutionRow).where(
            PaymentExecutionRow.workspace_id == workspace_id, PaymentExecutionRow.invoice_id == invoice_id
        )
    ).first()


def _store(
    ctx: ServiceContext,
    workspace_id: str,
    invoice_id: str,
    receipt: PaymentReceipt,
    attempt: int,
    row: PaymentExecutionRow | None,
) -> None:
    if row is None:
        row = PaymentExecutionRow(workspace_id=workspace_id, invoice_id=invoice_id)
        ctx.session.add(row)
    row.rail = receipt.rail
    row.status = receipt.status
    row.external_id = receipt.external_id
    row.dashboard_url = receipt.dashboard_url
    row.error = receipt.error
    row.instruction = receipt.instruction.model_dump(mode="json") if receipt.instruction else None
    row.attempts = attempt
    row.executed_at = receipt.executed_at
    ctx.session.flush()


def _execution(row: PaymentExecutionRow) -> PaymentExecution:
    return PaymentExecution.model_validate(
        {
            "rail": row.rail,
            "status": row.status,
            "external_id": row.external_id,
            "dashboard_url": row.dashboard_url,
            "executed_at": row.executed_at,
            "error": row.error,
            "instruction": row.instruction,
        }
    )


def _number(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
