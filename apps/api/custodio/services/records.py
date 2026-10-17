"""Invoices and decisions as stored, and what derives from them: payment history, balance, company state, metrics.

The balance is never stored: it is the opening balance minus every payment this workspace made, so it cannot drift
away from the decisions that justify it.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, select, update

from custodio.contracts import (
    AgentVerdict,
    CompanyState,
    Decision,
    DecisionStatus,
    InvoiceCase,
    Metrics,
    PaymentRecord,
)
from custodio.db.models import DecisionRow, InvoiceRow, WorkspaceRow
from custodio.services.context import ServiceContext
from custodio.services.errors import DecisionNotFound

PAID = frozenset({DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN})
AUTONOMOUS = frozenset({DecisionStatus.PAID_AUTO, DecisionStatus.HOLD})


def store_invoice(
    ctx: ServiceContext, workspace_id: str, case: InvoiceCase, *, document_id: str | None, read_ok: bool
) -> InvoiceRow:
    row = InvoiceRow(
        workspace_id=workspace_id,
        id=case.id,
        document_id=document_id,
        received_at=case.received_at,
        extraction=case.extraction.model_dump(mode="json"),
        read_ok=read_ok,
        expected=case.expected,
        trap=case.trap,
    )
    ctx.session.add(row)
    ctx.session.flush()
    return row


def as_case(row: InvoiceRow) -> InvoiceCase:
    """What the engine sees: dataset labels never leave the database."""
    return InvoiceCase.model_validate({"id": row.id, "received_at": row.received_at, "extraction": row.extraction})


def invoice(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> InvoiceRow:
    row = ctx.session.get(InvoiceRow, (workspace_id, invoice_id))
    if row is None:
        raise DecisionNotFound()
    return row


def invoices(ctx: ServiceContext, workspace_id: str) -> list[InvoiceRow]:
    query = select(InvoiceRow).where(InvoiceRow.workspace_id == workspace_id).order_by(InvoiceRow.received_at)
    return list(ctx.session.scalars(query))


def pending_invoices(ctx: ServiceContext, workspace_id: str) -> list[InvoiceRow]:
    decided = select(DecisionRow.invoice_id).where(DecisionRow.workspace_id == workspace_id)
    query = (
        select(InvoiceRow)
        .where(InvoiceRow.workspace_id == workspace_id, InvoiceRow.id.not_in(decided))
        .order_by(InvoiceRow.received_at)
    )
    return list(ctx.session.scalars(query))


def save_decision(ctx: ServiceContext, workspace_id: str, decision: Decision, *, audit_blocked: bool) -> None:
    row = ctx.session.get(DecisionRow, (workspace_id, decision.invoice_id))
    if row is None:
        row = DecisionRow(workspace_id=workspace_id, invoice_id=decision.invoice_id)
        ctx.session.add(row)
    row.status = decision.status.value
    row.document = decision.model_dump(mode="json")
    row.audit_blocked = audit_blocked or bool(row.audit_blocked)
    row.decided_at = ctx.now()
    ctx.session.flush()


def claim_pending(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> bool:
    """Takes the write lock on a pending decision for this unit of work.

    A concurrent approval of the same decision waits here until this one commits, then finds it no longer pending.
    Reading the status and deciding afterwards would let both approvals pay.
    """
    claimed = ctx.session.connection().execute(
        update(DecisionRow)
        .where(
            DecisionRow.workspace_id == workspace_id,
            DecisionRow.invoice_id == invoice_id,
            DecisionRow.status == DecisionStatus.PENDING_APPROVAL.value,
        )
        .values(status=DecisionRow.status)
    )
    return claimed.rowcount == 1


def decision(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> Decision:
    row = ctx.session.get(DecisionRow, (workspace_id, invoice_id))
    if row is None:
        raise DecisionNotFound()
    return Decision.model_validate(row.document)


def decisions(ctx: ServiceContext, workspace_id: str, status: DecisionStatus | None = None) -> list[Decision]:
    query = _decided(workspace_id)
    if status is not None:
        query = query.where(DecisionRow.status == status.value)
    return [Decision.model_validate(row.document) for row, _ in ctx.session.execute(query)]


def seeded_history(workspace: WorkspaceRow) -> list[PaymentRecord]:
    return [PaymentRecord.model_validate(record) for record in workspace.history_seed]


def payment_history(ctx: ServiceContext, workspace: WorkspaceRow) -> list[PaymentRecord]:
    query = _decided(workspace.id).where(DecisionRow.status.in_([status.value for status in PAID]))
    made = [_payment(row, invoice_row) for row, invoice_row in ctx.session.execute(query)]
    return seeded_history(workspace) + made


def balance(ctx: ServiceContext, workspace: WorkspaceRow) -> Decimal:
    query = _decided(workspace.id).where(DecisionRow.status.in_([status.value for status in PAID]))
    paid = (Decision.model_validate(row.document).amount_base for row, _ in ctx.session.execute(query))
    return workspace.opening_balance - sum((amount or Decimal(0) for amount in paid), Decimal(0))


def company_state(ctx: ServiceContext, workspace: WorkspaceRow) -> CompanyState:
    return CompanyState(
        workspace_id=workspace.id,
        company_name=workspace.company_name,
        today=ctx.now().date(),
        opening_balance=balance(ctx, workspace),
        fx_units_per_base={currency: Decimal(units) for currency, units in workspace.fx_units_per_base.items()},
        history=payment_history(ctx, workspace),
    )


def metrics(ctx: ServiceContext, workspace_id: str) -> Metrics:
    rows = ctx.session.execute(_decided(workspace_id)).all()
    stored = [(Decision.model_validate(row.document), row, invoice_row) for row, invoice_row in rows]
    labelled = [(decided.agent_verdict, invoice_row.expected) for decided, _, invoice_row in stored]
    return count_metrics(
        [decided for decided, _, _ in stored],
        improper_payments=sum(row.audit_blocked for _, row, _ in stored),
        accuracy=_accuracy([(verdict, expected) for verdict, expected in labelled if expected is not None]),
    )


def count_metrics(decisions: Sequence[Decision], *, improper_payments: int, accuracy: float | None = None) -> Metrics:
    """`improper_payments` counts payments the engine wanted and the independent auditor stopped."""
    statuses = [decided.status for decided in decisions]
    total = len(statuses)
    return Metrics(
        total=total,
        paid_auto=statuses.count(DecisionStatus.PAID_AUTO),
        paid_human=statuses.count(DecisionStatus.PAID_HUMAN),
        hold=statuses.count(DecisionStatus.HOLD),
        pending=statuses.count(DecisionStatus.PENDING_APPROVAL),
        rejected=statuses.count(DecisionStatus.REJECTED),
        autonomy_rate=sum(status in AUTONOMOUS for status in statuses) / total if total else 0.0,
        accuracy=accuracy,
        improper_payments=improper_payments,
    )


def _accuracy(labelled: list[tuple[AgentVerdict, str]]) -> float | None:
    if not labelled:
        return None
    return sum(verdict.value == expected for verdict, expected in labelled) / len(labelled)


def _decided(workspace_id: str) -> Select[DecisionRow, InvoiceRow]:
    return (
        select(DecisionRow, InvoiceRow)
        .join(
            InvoiceRow,
            (InvoiceRow.workspace_id == DecisionRow.workspace_id) & (InvoiceRow.id == DecisionRow.invoice_id),
        )
        .where(DecisionRow.workspace_id == workspace_id)
        .order_by(InvoiceRow.received_at, InvoiceRow.id)
    )


def _payment(row: DecisionRow, invoice_row: InvoiceRow) -> PaymentRecord:
    paid = Decision.model_validate(row.document)
    number = invoice_row.extraction.get("invoice_number", {}).get("value")
    return PaymentRecord(
        invoice_id=paid.invoice_id,
        beneficiary_id=paid.beneficiary_id,
        invoice_number=number,
        amount=paid.amount or Decimal(0),
        currency=paid.currency or "",
        amount_base=paid.amount_base or Decimal(0),
        paid_on=row.decided_at.date(),
        by="person" if paid.status is DecisionStatus.PAID_HUMAN else "agent",
    )
