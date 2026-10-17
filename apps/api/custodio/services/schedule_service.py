"""The payment calendar: when each approved payment leaves, the cash it leaves behind and what the timing is worth.

The plan itself is custodio.engine.schedule. A payment the engine and the auditor approved goes out at once only when
its day has come; otherwise its payment entry in the ledger says the day it is scheduled for, and it waits here until
`run_due` sends it through the deployment's rail with the payment service, unchanged.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from datetime import date, timedelta
from decimal import Decimal

from pydantic import BaseModel

from custodio.contracts import Amount, Decision, InvoiceSource, LedgerKind, Policy
from custodio.db.models import DecisionRow, InvoiceRow, WorkspaceRow
from custodio.engine.formatting import HUNDRED
from custodio.engine.schedule import (
    Obligation,
    PlannedPayment,
    Timing,
    Treasury,
    captured_value,
    plan,
    projected_balance,
    settled,
)
from custodio.services import ledger_service, payment_service, policy_service, records
from custodio.services.context import ServiceContext

HORIZON_DAYS = 45
SCHEDULED_FOR = "scheduled_for"
APY_NOTE = (
    "Supuesto configurable (CUSTODIO_TREASURY_YIELD_APY), no un dato de Blinka: el rendimiento anual que se asume "
    "para el saldo que se queda en la cuenta hasta el día de pago."
)


class ScheduledItem(BaseModel):
    invoice_id: str
    beneficiary_id: str | None
    supplier_name: str
    amount: Amount | None
    currency: str | None
    amount_base: Amount
    due_date: date | None
    pay_on: date | None  # None while it waits for cash
    timing: Timing
    reason: str
    rail: str
    discount_base: Amount
    late_fee_avoided_base: Amount
    yield_base: Amount


class BalanceDay(BaseModel):
    day: date
    balance: Amount


class CapturedThisMonth(BaseModel):
    year: int
    month: int
    discounts: Amount
    late_fees_avoided: Amount
    treasury_yield: Amount
    total: Amount
    payments: int


class ScheduleView(BaseModel):
    today: date
    horizon_days: int
    base_currency: str
    rail: str
    cash: Amount  # in the account now, scheduled payments included
    committed_balance: Amount  # after every approved payment: what R12 checks against the reserve
    reserve: Amount
    apy: float
    apy_note: str
    items: list[ScheduledItem]  # in payment order, within the horizon
    waiting: list[ScheduledItem]  # what does not fit without touching the reserve
    balance: list[BalanceDay]  # one point per day, today included
    captured: CapturedThisMonth


class RunDue(BaseModel):
    executed: list[Decision]
    schedule: ScheduleView


def timing(ctx: ServiceContext, decision: Decision, invoice: InvoiceRow, policy: Policy) -> PlannedPayment:
    """When a payment approved right now should go out, on its own (the engine already checked the reserve)."""
    today = ctx.now().date()
    obligation = _obligation(decision, invoice, policy, approved_on=today)
    treasury = Treasury(today, obligation.amount_base, Decimal(0), _apy(ctx), policy.base_currency)
    return plan([obligation], treasury)[0]


def for_rail(decision: Decision, planned: PlannedPayment) -> Decision:
    """What the rail pays: the approved amount, less the early-payment discount when the plan earns one."""
    if planned.timing is not Timing.DISCOUNT or planned.obligation.discount is None:
        return decision
    kept = 1 - planned.obligation.discount.percent / HUNDRED
    return decision.model_copy(
        update={
            "amount": _times(decision.amount, kept),
            "amount_base": _times(decision.amount_base, kept),
        }
    )


def view(ctx: ServiceContext, workspace: WorkspaceRow) -> ScheduleView:
    return _view(ctx, workspace, policy_service.current(ctx, workspace.id))


def run_due(ctx: ServiceContext, workspace: WorkspaceRow, only: Collection[str] | None = None) -> RunDue:
    """Sends what is due today or earlier through the rail; what waits for cash or for its day stays.

    `only` limits the run to those invoices (the simulated month pays its own and leaves the real ones alone).
    """
    policy = policy_service.current(ctx, workspace.id)
    today = ctx.now().date()
    executed = [
        _execute(ctx, workspace, decision, planned, policy)
        for planned, decision in _planned(ctx, workspace, policy)
        if payment_service.may_execute(workspace)
        and planned.pay_on is not None
        and planned.pay_on <= today
        and (only is None or decision.invoice_id in only)
    ]
    return RunDue(executed=executed, schedule=_view(ctx, workspace, policy))


# Building the plan -----------------------------------------------------------------------------------------------


def _view(ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy) -> ScheduleView:
    today = ctx.now().date()
    pairs = _planned(ctx, workspace, policy)
    planned = [p for p, _ in pairs]
    treasury = _treasury(ctx, workspace, policy, sum((p.obligation.amount_base for p in planned), Decimal(0)))
    horizon = today + timedelta(days=HORIZON_DAYS)
    rail = ctx.runtime.payment_rail.name
    value = captured_value([*planned, *_settled_this_month(ctx, workspace, policy)], today.year, today.month)
    return ScheduleView(
        today=today,
        horizon_days=HORIZON_DAYS,
        base_currency=policy.base_currency,
        rail=rail,
        cash=treasury.cash,
        committed_balance=records.balance(ctx, workspace),
        reserve=policy.reserve,
        apy=float(treasury.apy),
        apy_note=APY_NOTE,
        items=[_item(p, rail) for p in planned if p.pay_on is not None and p.pay_on <= horizon],
        waiting=[_item(p, rail) for p in planned if p.pay_on is None],
        balance=[
            BalanceDay(day=point.day, balance=point.balance)
            for point in projected_balance(planned, treasury, HORIZON_DAYS)
        ],
        captured=CapturedThisMonth(
            year=today.year,
            month=today.month,
            discounts=value.discounts,
            late_fees_avoided=value.late_fees_avoided,
            treasury_yield=value.treasury_yield,
            total=value.total,
            payments=value.payments,
        ),
    )


def _planned(ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy) -> list[tuple[PlannedPayment, Decision]]:
    waiting = list(_waiting(ctx, workspace))
    obligations = [_obligation(d, invoice, policy, approved_on=row.decided_at.date()) for d, row, invoice in waiting]
    by_id = {d.invoice_id: d for d, _, _ in waiting}
    treasury = _treasury(ctx, workspace, policy, sum((o.amount_base for o in obligations), Decimal(0)))
    return [(p, by_id[p.obligation.invoice_id]) for p in plan(obligations, treasury)]


def _treasury(ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy, outstanding: Decimal) -> Treasury:
    """`outstanding`: what the scheduled payments still keep in the account on top of the committed balance."""
    return Treasury(
        today=ctx.now().date(),
        cash=records.balance(ctx, workspace) + outstanding,
        reserve=policy.reserve,
        apy=_apy(ctx),
        base_currency=policy.base_currency,
    )


def _waiting(ctx: ServiceContext, workspace: WorkspaceRow) -> Iterable[tuple[Decision, DecisionRow, InvoiceRow]]:
    """Approved payments marked as scheduled that no rail has executed yet. An intent is paid by its own agent."""
    scheduled = _scheduled_ids(ctx, workspace.id)
    for row, invoice in records.decided_rows(ctx, workspace.id):
        decision = Decision.model_validate(row.document)
        if (
            decision.invoice_id in scheduled
            and decision.status in records.PAID
            and decision.execution is None
            and invoice.extraction.get("source") != InvoiceSource.INTENT.value
        ):
            yield decision, row, invoice


def _scheduled_ids(ctx: ServiceContext, workspace_id: str) -> set[str]:
    payments = ledger_service.entries(ctx, workspace_id, kinds=(LedgerKind.PAYMENT,))
    return {entry.subject_id for entry in payments if entry.subject_id and entry.payload.get(SCHEDULED_FOR)}


def _settled_this_month(ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy) -> list[PlannedPayment]:
    today = ctx.now().date()
    settled_payments = []
    for row, invoice in records.decided_rows(ctx, workspace.id):
        decision = Decision.model_validate(row.document)
        execution = decision.execution
        if execution is None or execution.status not in payment_service.SETTLED:
            continue
        paid_on = execution.executed_at.date()
        if (paid_on.year, paid_on.month) == (today.year, today.month):
            obligation = _obligation(decision, invoice, policy, approved_on=row.decided_at.date())
            settled_payments.append(settled(obligation, paid_on, _treasury(ctx, workspace, policy, Decimal(0))))
    return settled_payments


def _obligation(decision: Decision, invoice: InvoiceRow, policy: Policy, *, approved_on: date) -> Obligation:
    deal = next((b.agreement for b in policy.beneficiaries if b.id == decision.beneficiary_id), None)
    return Obligation(
        invoice_id=decision.invoice_id,
        beneficiary_id=decision.beneficiary_id,
        supplier_name=decision.supplier_name or "",
        amount=decision.amount,
        currency=decision.currency,
        amount_base=decision.amount_base or Decimal(0),
        approved_on=approved_on,
        issue_date=_read_date(invoice, "issue_date"),
        due_date=_read_date(invoice, "due_date"),
        discount=deal.early_payment_discount if deal else None,
        late_fee_pct=deal.late_fee_pct if deal else None,
        critical=deal.critical if deal else False,
    )


# Executing -------------------------------------------------------------------------------------------------------


def _execute(
    ctx: ServiceContext, workspace: WorkspaceRow, decision: Decision, planned: PlannedPayment, policy: Policy
) -> Decision:
    execution = payment_service.execute(ctx, workspace.id, for_rail(decision, planned), policy)
    paid = decision.model_copy(update={"execution": execution})
    records.attach_execution(ctx, workspace.id, paid)
    ledger_service.append(
        ctx,
        workspace.id,
        LedgerKind.PAYMENT,
        decision.invoice_id,
        {
            **payment_service.payment_payload(paid),
            "scheduled": True,
            "timing": planned.timing.value,
            "discount_base": str(planned.discount_base),
        },
    )
    return paid


def _item(planned: PlannedPayment, rail: str) -> ScheduledItem:
    obligation = planned.obligation
    return ScheduledItem(
        invoice_id=obligation.invoice_id,
        beneficiary_id=obligation.beneficiary_id,
        supplier_name=obligation.supplier_name,
        amount=obligation.amount,
        currency=obligation.currency,
        amount_base=obligation.amount_base,
        due_date=obligation.due_date,
        pay_on=planned.pay_on,
        timing=planned.timing,
        reason=planned.reason,
        rail=rail,
        discount_base=planned.discount_base,
        late_fee_avoided_base=planned.late_fee_avoided_base,
        yield_base=planned.yield_base,
    )


def _read_date(invoice: InvoiceRow, field: str) -> date | None:
    value = (invoice.extraction.get(field) or {}).get("value")
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _times(value: Decimal | None, factor: Decimal) -> Decimal | None:
    return None if value is None else (value * factor).quantize(Decimal("0.01"))


def _apy(ctx: ServiceContext) -> Decimal:
    return ctx.runtime.treasury_yield_apy
