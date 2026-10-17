"""Bank reconciliation and month-end close of a visitor's workspace.

The model only reads statements in PDF or image (`lanes.read_statement`); a CSV is read by code. Pairing, the
month's figures and the evidence pack are the pure functions of `custodio.reconciliation`. Every reconciliation,
every bank confirmation, every review and every close is written to the ledger, and a closed month takes no more.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy import select

from custodio import reconciliation
from custodio.contracts import Beneficiary, Decision, DecisionStatus, LedgerEntry, LedgerKind, Policy
from custodio.db.models import DecisionRow, DocumentRow, InvoiceRow, LedgerEntryRow, ReconciliationRow, WorkspaceRow
from custodio.engine.formatting import counted
from custodio.engine.ledger import canonical_json
from custodio.extraction.errors import ExtractionError
from custodio.reconciliation import demo
from custodio.reconciliation.errors import StatementError
from custodio.reconciliation.errors import UnsupportedStatement as StatementNotSupported
from custodio.reconciliation.models import (
    NEEDS_REVIEW,
    MatchSettings,
    MovementResult,
    PaidInvoice,
    PaymentResult,
    PaymentStatus,
    PeriodClose,
    PeriodSummary,
    ReconciliationOutcome,
    Review,
    Statement,
    StatementMovement,
    UnpaidInvoice,
)
from custodio.services import invoice_service, ledger_service, policy_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import (
    MovementNotReviewable,
    PayloadTooLarge,
    PeriodClosed,
    PeriodNotClosed,
    ReconciliationConflict,
    ReconciliationNotFound,
    StatementUnreadable,
    UnsupportedStatement,
)
from custodio.services.workspace_service import new_id

MAX_STATEMENT_BYTES = invoice_service.MAX_DOCUMENT_BYTES
CSV_MEDIA_TYPES = frozenset({"text/csv", "application/csv", "text/comma-separated-values", "application/vnd.ms-excel"})
CSV_SUFFIXES = (".csv", ".txt")
DOCUMENT_MEDIA_TYPES = invoice_service.DOCUMENT_MEDIA_TYPES
DEMO_FILENAME = "extracto-demo.csv"
UNPAID = frozenset({DecisionStatus.PENDING_APPROVAL, DecisionStatus.HOLD, DecisionStatus.REJECTED})
EVIDENCE_PATH = "/api/v1/periods/{}/evidence.zip"
DemoFormat = Literal["csv", "pdf"]


class StatementSource(StrEnum):
    CSV = "csv"
    DOCUMENT = "document"  # a PDF or an image, read by the model
    DEMO = "demo"


@dataclass(frozen=True)
class Upload:
    data: bytes
    filename: str
    media_type: str


class MovementView(BaseModel):
    movement: StatementMovement
    result: MovementResult
    needs_review: bool
    review: Review | None = None
    acta_url: str | None = None
    external_id: str | None = None  # the rail's transfer id of the payment it reconciles, e.g. "tr_…"
    dashboard_url: str | None = None


class ReconciliationView(BaseModel):
    id: str
    created_at: datetime
    period: str
    source: StatementSource
    filename: str
    reader: str
    currency: str
    warnings: list[str]
    demo_shift_days: int | None  # how many days the demo statement moved to follow this workspace's batch
    settings: MatchSettings
    movements: list[MovementView]
    payments: list[PaymentResult]
    summary: PeriodSummary
    can_close: bool
    period_closed: PeriodClose | None
    ledger_seq: int


class ReconciliationItem(BaseModel):
    id: str
    created_at: datetime
    period: str
    source: StatementSource
    filename: str
    movements: int
    alerts_open: int
    period_closed: bool


class PeriodCloseView(BaseModel):
    close: PeriodClose
    summary: PeriodSummary
    evidence_path: str


class DemoStatement(BaseModel):
    filename: str
    media_type: str
    data: bytes


@dataclass(frozen=True)
class _Decided:
    decision: Decision
    row: DecisionRow
    invoice: InvoiceRow


# --- reconciling ------------------------------------------------------------------------------------------------


def reconcile_upload(
    ctx: ServiceContext, workspace: WorkspaceRow, upload: Upload, settings: MatchSettings
) -> ReconciliationView:
    if len(upload.data) > MAX_STATEMENT_BYTES:
        raise PayloadTooLarge()
    currency = policy_service.current(ctx, workspace.id).base_currency
    source = _source_of(upload)
    if source is StatementSource.CSV:
        statement = _read(lambda: reconciliation.read_csv_statement(upload.data, default_currency=currency))
    else:
        statement = _read(
            lambda: ctx.lanes.read_statement(
                upload.data, filename=upload.filename, media_type=upload.media_type, default_currency=currency
            )
        )
    document = _store_document(ctx, workspace.id, upload)
    return _record(ctx, workspace, statement, upload.data, source, upload.filename, document.id, None, settings)


def reads_with_model(upload: Upload) -> bool:
    return _source_of(upload) is StatementSource.DOCUMENT


def reconcile_demo(ctx: ServiceContext, workspace: WorkspaceRow, settings: MatchSettings) -> ReconciliationView:
    shift = _demo_shift(ctx, workspace)
    data = demo.demo_statement_csv(shift)
    currency = policy_service.current(ctx, workspace.id).base_currency
    statement = reconciliation.read_csv_statement(data, default_currency=currency)
    return _record(ctx, workspace, statement, data, StatementSource.DEMO, DEMO_FILENAME, None, shift, settings)


def demo_statement(ctx: ServiceContext, workspace: WorkspaceRow, format_: DemoFormat) -> DemoStatement:
    """The demo statement as this workspace would get it: moved to the day its batch was paid."""
    shift = _demo_shift(ctx, workspace)
    if format_ == "pdf":
        return DemoStatement(
            filename="extracto-demo.pdf", media_type="application/pdf", data=demo.demo_statement_pdf(shift)
        )
    return DemoStatement(filename=DEMO_FILENAME, media_type="text/csv", data=demo.demo_statement_csv(shift))


def get(ctx: ServiceContext, workspace: WorkspaceRow, reconciliation_id: str) -> ReconciliationView:
    return _view(ctx, workspace, _row(ctx, workspace.id, reconciliation_id))


def history(ctx: ServiceContext, workspace: WorkspaceRow) -> list[ReconciliationItem]:
    rows = ctx.session.scalars(
        select(ReconciliationRow)
        .where(ReconciliationRow.workspace_id == workspace.id)
        .order_by(ReconciliationRow.ledger_seq.desc())
    )
    return [_item(ctx, workspace, row) for row in rows]


def resolve(
    ctx: ServiceContext, workspace: WorkspaceRow, reconciliation_id: str, *, movement_id: str, reviewer: str, note: str
) -> ReconciliationView:
    row = _row(ctx, workspace.id, reconciliation_id)
    _ensure_open(ctx, workspace.id, row.period)
    statement, outcome, reviews = _stored(row)
    result = next((item for item in outcome.movements if item.movement_id == movement_id), None)
    if result is None or result.status not in NEEDS_REVIEW or any(r.movement_id == movement_id for r in reviews):
        raise MovementNotReviewable()
    movement = next(item for item in statement.movements if item.id == movement_id)
    entry = _append(
        ctx,
        workspace.id,
        LedgerKind.RECONCILIATION_REVIEW,
        row.id,
        {
            "movement_id": movement.id,
            "row": movement.row,
            "description": movement.description,
            "amount": movement.amount,
            "currency": movement.currency,
            "status": result.status,
            "reviewer": reviewer,
            "note": note,
        },
    )
    review = Review(movement_id=movement_id, reviewer=reviewer, note=note, at=entry.at, ledger_seq=entry.seq)
    row.reviews = [*row.reviews, review.model_dump(mode="json")]
    ctx.session.flush()
    return _view(ctx, workspace, row)


# --- closing the month ------------------------------------------------------------------------------------------


def close_period(ctx: ServiceContext, workspace: WorkspaceRow, period: str, *, closed_by: str) -> PeriodCloseView:
    _ensure_open(ctx, workspace.id, period)
    row = _latest(ctx, workspace.id, period)
    if row is None:
        raise ReconciliationConflict(f"Sube el extracto de {period} antes de cerrarlo.")
    summary = _summary(ctx, workspace, row)
    if summary.alerts_open:
        waiting = counted(summary.alerts_open, "movimiento sin revisar", "movimientos sin revisar")
        raise ReconciliationConflict(f"Quedan {waiting}: revisa cada salida sin factura antes de cerrar el mes.")
    if not ledger_service.verify(ctx, workspace.id).valid:
        raise ReconciliationConflict("El registro no verifica: no se cierra un mes sobre una cadena rota.")
    entry = _append(
        ctx,
        workspace.id,
        LedgerKind.PERIOD_CLOSED,
        _period_subject(period),
        {
            "period": period,
            "reconciliation_id": row.id,
            "closed_by": closed_by,
            "summary": summary.model_dump(mode="json"),
        },
    )
    close = _closure_from(entry)
    return PeriodCloseView(close=close, summary=summary, evidence_path=EVIDENCE_PATH.format(period))


def evidence(ctx: ServiceContext, workspace: WorkspaceRow, period: str) -> bytes:
    closed = _closure(ctx, workspace.id, period)
    if closed is None:
        raise PeriodNotClosed()
    row = _row(ctx, workspace.id, closed.reconciliation_id)
    statement, outcome, reviews = _stored(row)
    decided = _decided_in(ctx, workspace.id, period)
    ledger = ledger_service.entries(ctx, workspace.id)
    source = reconciliation.EvidenceSource(
        company_name=workspace.company_name,
        period=period,
        statement=statement,
        outcome=outcome,
        reviews=reviews,
        summary=reconciliation.summarize(
            [item.decision for item in decided], statement, outcome, reviews, currency=statement.currency
        ),
        actas={item.decision.invoice_id: _acta(ctx, workspace.id, item) for item in decided},
        ledger=ledger,
        verification=ctx.lanes.verify_ledger(ledger),
        closed=closed,
    )
    return reconciliation.evidence_pack(source, ctx.now())


def evidence_filename(period: str) -> str:
    return f"custodio-cierre-{period}.zip"


# --- recording --------------------------------------------------------------------------------------------------


def _record(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    statement: Statement,
    data: bytes,
    source: StatementSource,
    filename: str,
    document_id: str | None,
    shift: int | None,
    settings: MatchSettings,
) -> ReconciliationView:
    period = _period_of(statement, ctx.now().date())
    _ensure_open(ctx, workspace.id, period)
    decided = _decided(ctx, workspace.id)
    policy = policy_service.current(ctx, workspace.id)
    paid = [made for item in decided if (made := _paid(ctx, item, policy)) and _in_reach(made, period, settings)]
    unpaid = [invoice for item in decided if (invoice := _unpaid(item, policy)) is not None]
    outcome = reconciliation.reconcile(statement.movements, paid, unpaid, settings)
    reconciliation_id = new_id()
    entry = _append(
        ctx,
        workspace.id,
        LedgerKind.RECONCILIATION,
        reconciliation_id,
        _summary_payload(statement, outcome, data, source, filename, period),
    )
    for confirmed in outcome.payments:
        if confirmed.status is PaymentStatus.CONFIRMED:
            payload = _confirmation(reconciliation_id, confirmed, statement)
            _append(ctx, workspace.id, LedgerKind.RECONCILIATION, confirmed.invoice_id, payload)
    row = ReconciliationRow(
        id=reconciliation_id,
        workspace_id=workspace.id,
        period=period,
        source=source.value,
        filename=filename[:255],
        document_id=document_id,
        demo_shift_days=shift,
        statement=statement.model_dump(mode="json"),
        outcome=outcome.model_dump(mode="json"),
        reviews=[],
        ledger_seq=entry.seq,
        created_at=ctx.now(),
    )
    ctx.session.add(row)
    ctx.session.flush()
    return _view(ctx, workspace, row)


def _summary_payload(
    statement: Statement,
    outcome: ReconciliationOutcome,
    data: bytes,
    source: StatementSource,
    filename: str,
    period: str,
) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for item in outcome.movements:
        statuses[item.status.value] = statuses.get(item.status.value, 0) + 1
    return {
        "period": period,
        "source": source,
        "filename": filename,
        "reader": statement.reader,
        "currency": statement.currency,
        "movements": len(statement.movements),
        "statuses": statuses,
        "confirmed_payments": sum(p.status is PaymentStatus.CONFIRMED for p in outcome.payments),
        "pending_payments": sum(p.status is PaymentStatus.PENDING for p in outcome.payments),
        "settings": outcome.settings.model_dump(mode="json"),
        "statement_sha256": hashlib.sha256(data).hexdigest(),
        "outcome_sha256": hashlib.sha256(canonical_json(outcome.model_dump()).encode()).hexdigest(),
    }


def _confirmation(reconciliation_id: str, payment: PaymentResult, statement: Statement) -> dict[str, Any]:
    rows = {movement.id: movement.row for movement in statement.movements}
    return {
        "reconciliation_id": reconciliation_id,
        "status": payment.status,
        "level": payment.level,
        "movement_rows": [rows[movement_id] for movement_id in payment.movement_ids],
        "expected": payment.expected,
        "difference": payment.difference,
        "currency": payment.currency,
        "reason": payment.reason,
    }


# --- views ------------------------------------------------------------------------------------------------------


def _view(ctx: ServiceContext, workspace: WorkspaceRow, row: ReconciliationRow) -> ReconciliationView:
    statement, outcome, reviews = _stored(row)
    results = {item.movement_id: item for item in outcome.movements}
    payments = {payment.invoice_id: payment for payment in outcome.payments}
    reviewed = {review.movement_id: review for review in reviews}
    summary = _summary(ctx, workspace, row)
    closed = _closure(ctx, workspace.id, row.period)
    latest = _latest(ctx, workspace.id, row.period)
    return ReconciliationView(
        id=row.id,
        created_at=row.created_at,
        period=row.period,
        source=StatementSource(row.source),
        filename=row.filename,
        reader=statement.reader,
        currency=statement.currency,
        warnings=statement.warnings,
        demo_shift_days=row.demo_shift_days,
        settings=outcome.settings,
        movements=[
            _movement_view(movement, results[movement.id], payments, reviewed.get(movement.id))
            for movement in statement.movements
        ],
        payments=outcome.payments,
        summary=summary,
        can_close=closed is None and summary.alerts_open == 0 and latest is not None and latest.id == row.id,
        period_closed=closed,
        ledger_seq=row.ledger_seq,
    )


def _movement_view(
    movement: StatementMovement, result: MovementResult, payments: dict[str, PaymentResult], review: Review | None
) -> MovementView:
    payment = payments.get(result.invoice_id or "")
    return MovementView(
        movement=movement,
        result=result,
        needs_review=result.status in NEEDS_REVIEW,
        review=review,
        acta_url=payment.acta_url if payment else None,
        external_id=payment.external_id if payment else None,
        dashboard_url=payment.dashboard_url if payment else None,
    )


def _item(ctx: ServiceContext, workspace: WorkspaceRow, row: ReconciliationRow) -> ReconciliationItem:
    statement, _, _ = _stored(row)
    return ReconciliationItem(
        id=row.id,
        created_at=row.created_at,
        period=row.period,
        source=StatementSource(row.source),
        filename=row.filename,
        movements=len(statement.movements),
        alerts_open=_summary(ctx, workspace, row).alerts_open,
        period_closed=_closure(ctx, workspace.id, row.period) is not None,
    )


def _summary(ctx: ServiceContext, workspace: WorkspaceRow, row: ReconciliationRow) -> PeriodSummary:
    statement, outcome, reviews = _stored(row)
    decisions = [item.decision for item in _decided_in(ctx, workspace.id, row.period)]
    return reconciliation.summarize(decisions, statement, outcome, reviews, currency=statement.currency)


def _acta(ctx: ServiceContext, workspace_id: str, item: _Decided) -> dict[str, Any]:
    return {
        "decision": item.decision.model_dump(mode="json"),
        "factura": invoice_service.view(item.invoice, decided=True).model_dump(mode="json"),
        "registro": [
            entry.model_dump(mode="json")
            for entry in ledger_service.entries(ctx, workspace_id, subject_id=item.decision.invoice_id)
        ],
    }


# --- what was paid ----------------------------------------------------------------------------------------------


def _decided(ctx: ServiceContext, workspace_id: str) -> list[_Decided]:
    query = (
        select(DecisionRow, InvoiceRow)
        .join(
            InvoiceRow,
            (InvoiceRow.workspace_id == DecisionRow.workspace_id) & (InvoiceRow.id == DecisionRow.invoice_id),
        )
        .where(DecisionRow.workspace_id == workspace_id)
        .order_by(InvoiceRow.received_at, InvoiceRow.id)
    )
    return [
        _Decided(decision=Decision.model_validate(row.document), row=row, invoice=invoice)
        for row, invoice in ctx.session.execute(query)
    ]


def _decided_in(ctx: ServiceContext, workspace_id: str, period: str) -> list[_Decided]:
    return [item for item in _decided(ctx, workspace_id) if _period(item.row.decided_at.date()) == period]


def _paid(ctx: ServiceContext, item: _Decided, policy: Policy) -> PaidInvoice | None:
    decision = item.decision
    if decision.status not in records.PAID or decision.amount_base is None:
        return None
    execution = decision.execution
    beneficiary = _beneficiary(policy, decision)
    return PaidInvoice(
        **_invoice_fields(item, policy),
        tax_id=beneficiary.tax_id if beneficiary else None,
        paid_on=(execution.executed_at if execution else item.row.decided_at).astimezone(UTC).date(),
        external_id=execution.external_id if execution else None,
        dashboard_url=execution.dashboard_url if execution else None,
        acta_url=records.acta_url(ctx.runtime.public_base_url, decision.invoice_id),
    )


def _unpaid(item: _Decided, policy: Policy) -> UnpaidInvoice | None:
    if item.decision.status not in UNPAID or item.decision.amount_base is None:
        return None
    return UnpaidInvoice(**_invoice_fields(item, policy), status=item.decision.status)


def _invoice_fields(item: _Decided, policy: Policy) -> dict[str, Any]:
    decision = item.decision
    beneficiary = _beneficiary(policy, decision)
    names = [*((beneficiary.name, *beneficiary.aliases) if beneficiary else ()), decision.supplier_name or ""]
    amount_base = decision.amount_base if decision.amount_base is not None else Decimal(0)
    return {
        "invoice_id": decision.invoice_id,
        "invoice_number": item.invoice.extraction.get("invoice_number", {}).get("value"),
        "supplier_name": decision.supplier_name,
        "names": [name for name in dict.fromkeys(names) if name],
        "amount": decision.amount if decision.amount is not None else amount_base,
        "currency": decision.currency or policy.base_currency,
        "amount_base": amount_base,
        "base_currency": policy.base_currency,
    }


def _beneficiary(policy: Policy, decision: Decision) -> Beneficiary | None:
    return next((b for b in policy.beneficiaries if b.id == decision.beneficiary_id), None)


def _demo_shift(ctx: ServiceContext, workspace: WorkspaceRow) -> int:
    policy = policy_service.current(ctx, workspace.id)
    days = [payment.paid_on for item in _decided(ctx, workspace.id) if (payment := _paid(ctx, item, policy))]
    return demo.shift_for(min(days) if days else None)


# --- periods ----------------------------------------------------------------------------------------------------


def _period(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _period_of(statement: Statement, today: date) -> str:
    """The month of the statement's last dated movement (a statement covers one month), or this month."""
    days = [movement.booked_on for movement in statement.movements if movement.booked_on is not None]
    return _period(max(days) if days else today)


def _in_reach(payment: PaidInvoice, period: str, settings: MatchSettings) -> bool:
    """Paid in the month, or late enough in the previous one to show up in this statement."""
    year, month = (int(part) for part in period.split("-"))
    start = date(year, month, 1)
    end = date(year + month // 12, month % 12 + 1, 1)
    return start - timedelta(days=settings.date_window_days) <= payment.paid_on < end


def _period_subject(period: str) -> str:
    return f"periodo-{period}"


def _ensure_open(ctx: ServiceContext, workspace_id: str, period: str) -> None:
    if _closure(ctx, workspace_id, period) is not None:
        raise PeriodClosed()


def _closure(ctx: ServiceContext, workspace_id: str, period: str) -> PeriodClose | None:
    row = ctx.session.scalars(
        select(LedgerEntryRow).where(
            LedgerEntryRow.workspace_id == workspace_id,
            LedgerEntryRow.kind == LedgerKind.PERIOD_CLOSED.value,
            LedgerEntryRow.subject_id == _period_subject(period),
        )
    ).first()
    if row is None:
        return None
    return _closure_from(
        LedgerEntry(
            seq=row.seq,
            at=row.at,
            kind=LedgerKind(row.kind),
            subject_id=row.subject_id,
            payload=row.payload,
            prev_hash=row.prev_hash,
            hash=row.hash,
        )
    )


def _closure_from(entry: LedgerEntry) -> PeriodClose:
    return PeriodClose(
        period=entry.payload["period"],
        closed_at=entry.at,
        closed_by=entry.payload["closed_by"],
        reconciliation_id=entry.payload["reconciliation_id"],
        ledger_seq=entry.seq,
        ledger_hash=entry.hash,
    )


# --- storage ----------------------------------------------------------------------------------------------------


def _row(ctx: ServiceContext, workspace_id: str, reconciliation_id: str) -> ReconciliationRow:
    row = ctx.session.get(ReconciliationRow, reconciliation_id)
    if row is None or row.workspace_id != workspace_id:
        raise ReconciliationNotFound()
    return row


def _latest(ctx: ServiceContext, workspace_id: str, period: str) -> ReconciliationRow | None:
    return ctx.session.scalars(
        select(ReconciliationRow)
        .where(ReconciliationRow.workspace_id == workspace_id, ReconciliationRow.period == period)
        .order_by(ReconciliationRow.ledger_seq.desc())
        .limit(1)
    ).first()


def _stored(row: ReconciliationRow) -> tuple[Statement, ReconciliationOutcome, list[Review]]:
    return (
        Statement.model_validate(row.statement),
        ReconciliationOutcome.model_validate(row.outcome),
        [Review.model_validate(review) for review in row.reviews],
    )


def _append(
    ctx: ServiceContext, workspace_id: str, kind: LedgerKind, subject_id: str, payload: dict[str, Any]
) -> LedgerEntry:
    """Written as plain JSON (amounts as text), whatever the ledger implementation does with the rest."""
    return ledger_service.append(ctx, workspace_id, kind, subject_id, json.loads(canonical_json(payload)))


def _store_document(ctx: ServiceContext, workspace_id: str, upload: Upload) -> DocumentRow:
    document = DocumentRow(
        id=new_id(),
        workspace_id=workspace_id,
        filename=upload.filename[:255],
        media_type=upload.media_type,
        data=upload.data,
        created_at=ctx.now(),
    )
    ctx.session.add(document)
    ctx.session.flush()
    return document


def _source_of(upload: Upload) -> StatementSource:
    if upload.media_type in CSV_MEDIA_TYPES or upload.filename.lower().endswith(CSV_SUFFIXES):
        return StatementSource.CSV
    if upload.media_type in DOCUMENT_MEDIA_TYPES:
        return StatementSource.DOCUMENT
    raise UnsupportedStatement()


def _read(read: Callable[[], Statement]) -> Statement:
    try:
        return read()
    except StatementNotSupported as error:
        raise UnsupportedStatement(error.message) from error
    except StatementError as error:
        raise StatementUnreadable(error.message) from error
    except ExtractionError as error:
        raise StatementUnreadable(str(error)) from error
