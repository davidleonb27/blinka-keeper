"""«Simular 30 días»: the demo plays a seeded month through the very path a real month takes.

Each day's invoices are received, decided, approved by the demo's approver when the agent asks (every invoice but the
fraud) and paid when their day comes. Everything lands in the workspace's ledger, so the autonomy it earns and the
fraud that knocks it down are the real trust entries. It runs once per workspace (a `simulation` entry marks it), only
in the demo workspace and always on the simulated rail, whatever rail the deployment pays with.

Paying a month of invoices would push the demo's balance against its reserve, so the run first adds the month's cash
(customers' collections, assumed) and says so in the ledger.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from pydantic import BaseModel

from custodio.contracts import Amount, DecisionStatus, LedgerKind
from custodio.dataset.month import DAYS, SEED, MonthInvoice
from custodio.db.models import WorkspaceRow
from custodio.engine.units import to_base
from custodio.payments import simulated_choice
from custodio.services import (
    approval_service,
    invoice_service,
    ledger_service,
    policy_service,
    records,
    schedule_service,
    trust_service,
)
from custodio.services.context import ServiceContext
from custodio.services.errors import SimulationNotAvailable
from custodio.services.trust_service import TrustOverview
from custodio.services.workspace_service import WorkspaceKind, received_payload

SIMULATED_SUFFIX = " (simulación)"
DEFAULT_APPROVER = "Aprobador de la demo"
END_OF_DAY = time(22, 0)
INFLOW_NOTE = (
    "Cobros de clientes del mes simulado, supuestos para que la reserva no frene la simulación: el saldo inicial sube "
    "en lo mismo que suman las facturas del mes."
)


class SimulationResult(BaseModel):
    created: bool  # False when this workspace had already simulated its month
    seed: int
    start: date
    days: int
    invoices: int
    inflow_base: Amount
    trust: TrustOverview


def simulate_month(ctx: ServiceContext, workspace: WorkspaceRow) -> SimulationResult:
    if workspace.kind != WorkspaceKind.DEMO.value:
        raise SimulationNotAvailable()
    done = ledger_service.entries(ctx, workspace.id, kinds=(LedgerKind.SIMULATION,))
    if done:
        return _result(ctx, workspace, done[0].payload, created=False)
    simulated = replace(ctx.runtime, payment_rail=simulated_choice()).context(ctx.session)
    invoice_service.process_pending(simulated, workspace)  # the demo batch first, as a visitor would
    policy = policy_service.current(ctx, workspace.id)
    start = _first_of_next_month(ctx.now().date())
    month = ctx.lanes.simulated_month(records.company_state(ctx, workspace), policy, start)
    inflow = _inflow(month, workspace)
    workspace.opening_balance += inflow
    payload = {
        "seed": SEED,
        "start": start.isoformat(),
        "days": DAYS,
        "invoices": len(month),
        "inflow_base": str(inflow),
    }
    marker = ledger_service.append(ctx, workspace.id, LedgerKind.SIMULATION, None, {**payload, "note": INFLOW_NOTE})
    ids = {invoice.case.id for invoice in month}
    approver = (policy.approvers[0].name if policy.approvers else DEFAULT_APPROVER) + SIMULATED_SUFFIX
    for offset in range(DAYS):
        day = start + timedelta(days=offset)
        _play_day(simulated, workspace, [m for m in month if m.day == day], day, approver, ids)
    return _result(ctx, workspace, marker.payload, created=True)


def _play_day(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    today: list[MonthInvoice],
    day: date,
    approver: str,
    simulated_ids: set[str],
) -> None:
    on_the_day = replace(ctx.runtime, clock=lambda: datetime.combine(day, END_OF_DAY, tzinfo=UTC)).context(ctx.session)
    rows = []
    for invoice in today:
        rows.append(records.store_invoice(on_the_day, workspace.id, invoice.case, document_id=None, read_ok=True))
        ledger_service.append(
            on_the_day, workspace.id, LedgerKind.INVOICE_RECEIVED, invoice.case.id, received_payload(invoice.case)
        )
    if rows:
        outcome = invoice_service.decide(on_the_day, workspace, rows, execute_payments=True)
        frauds = {invoice.case.id for invoice in today if invoice.fraud}
        for decision in outcome.batch.decisions:
            if decision.status is DecisionStatus.PENDING_APPROVAL and decision.invoice_id not in frauds:
                approval_service.decide(on_the_day, workspace, decision.invoice_id, "approved", approver=approver)
    schedule_service.run_due(on_the_day, workspace, only=simulated_ids)


def _inflow(month: list[MonthInvoice], workspace: WorkspaceRow) -> Decimal:
    fx = {currency: Decimal(units) for currency, units in workspace.fx_units_per_base.items()}
    amounts = (_base_amount(invoice, fx) for invoice in month)
    return sum((amount for amount in amounts if amount is not None), Decimal(0)).quantize(Decimal("0.01"))


def _base_amount(invoice: MonthInvoice, fx: dict[str, Decimal]) -> Decimal | None:
    read = invoice.case.extraction
    return to_base(Decimal(read.amount.value) if read.amount.value else None, read.currency.value, fx)


def _first_of_next_month(today: date) -> date:
    return (today.replace(day=1) + timedelta(days=32)).replace(day=1)


def _result(
    ctx: ServiceContext, workspace: WorkspaceRow, payload: dict[str, object], *, created: bool
) -> SimulationResult:
    return SimulationResult(
        created=created,
        seed=int(str(payload["seed"])),
        start=date.fromisoformat(str(payload["start"])),
        days=int(str(payload["days"])),
        invoices=int(str(payload["invoices"])),
        inflow_base=Decimal(str(payload["inflow_base"])),
        trust=trust_service.overview(ctx, workspace),
    )
