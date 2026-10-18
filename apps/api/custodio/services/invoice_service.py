"""The single write path for invoices: receive → read → decide → audit → ledger.

The panel, the firewall, MCP, the public challenge and the red team all end in `decide`, so every surface
gets the same rules, the same independent audit and the same ledger.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

from custodio.contracts import (
    Approval,
    AuditReport,
    BatchResult,
    Decision,
    DecisionStatus,
    ExtractedField,
    ExtractedInvoice,
    InvoiceCase,
    InvoiceSource,
    LedgerKind,
    PaymentExecution,
    RuleOutcome,
)
from custodio.db.models import DocumentRow, InvoiceRow, WorkspaceRow
from custodio.engine.domains import first_email
from custodio.extraction.einvoice import is_einvoice, is_einvoice_reading, merge, same_invoice
from custodio.extraction.errors import ExtractionError
from custodio.llm import LLMError, LLMNotConfigured
from custodio.services import ledger_service, payment_service, policy_service, records, schedule_service, trust_service
from custodio.services.context import ServiceContext
from custodio.services.errors import (
    EInvoiceRejected,
    ModelNotConfigured,
    PayloadTooLarge,
    UnsupportedMediaType,
    model_failure,
)
from custodio.services.workspace_service import VISITOR_KINDS, new_id, received_payload

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
DOCUMENT_MEDIA_TYPES = frozenset({"application/pdf", "image/png", "image/jpeg", "image/webp"})
TEXT_MEDIA_TYPE = "text/plain"
XML_MEDIA_TYPE = "application/xml"
UNREAD_READER = "sin-lectura"
AUDITOR_STOP = "El auditor independiente no confirmó este pago y no se hizo"
HOLD_RULE_STOP = "Una regla de retención falló, así que este pago no se hizo"
Payout = tuple[PaymentExecution | None, dict[str, Any]]  # what the rail did now, and what the payment entry adds
FIELD_NAMES = tuple(name for name, info in ExtractedInvoice.model_fields.items() if info.annotation is ExtractedField)


class InvoiceView(BaseModel):
    id: str
    received_at: datetime
    document_id: str | None
    status: Literal["received", "decided"]
    read_ok: bool
    extraction: ExtractedInvoice


class Outcome(BaseModel):
    batch: BatchResult
    audit: AuditReport
    vetoed: list[str]  # payments the engine wanted that did not go out (auditor rejection or failing hold rule)


def receive_document(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    data: bytes,
    *,
    filename: str,
    media_type: str,
    source: InvoiceSource | None = None,
) -> InvoiceView:
    """`source` names the channel when it is not the file itself (a photo sent on WhatsApp)."""
    if len(data) > MAX_DOCUMENT_BYTES:
        raise PayloadTooLarge()
    if media_type == TEXT_MEDIA_TYPE:
        return receive_text(ctx, workspace, data.decode("utf-8", errors="replace"))
    if is_einvoice(media_type, filename):
        return receive_einvoice(ctx, workspace, data, filename=filename)
    if media_type not in DOCUMENT_MEDIA_TYPES:
        raise UnsupportedMediaType()
    document = _store_document(ctx, workspace.id, data, filename=filename, media_type=media_type)
    channel = source or (InvoiceSource.PDF if media_type == "application/pdf" else InvoiceSource.IMAGE)

    def read() -> ExtractedInvoice:
        reading = ctx.lanes.extract_document(data, filename=filename, media_type=media_type, document_id=document.id)
        return reading.model_copy(update={"source": channel})

    return _receive(ctx, workspace, document, read, source=channel, visible_text="")


def receive_text(
    ctx: ServiceContext, workspace: WorkspaceRow, text: str, source: InvoiceSource = InvoiceSource.TEXT
) -> InvoiceView:
    data = text.encode()
    if len(data) > MAX_DOCUMENT_BYTES:
        raise PayloadTooLarge()
    document = _store_document(ctx, workspace.id, data, filename="factura.txt", media_type=TEXT_MEDIA_TYPE)

    def read() -> ExtractedInvoice:
        return ctx.lanes.extract_text(text, document_id=document.id, source=source)

    return _receive(ctx, workspace, document, read, source=source, visible_text=text)


def receive_einvoice(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    data: bytes,
    *,
    filename: str,
    source: InvoiceSource = InvoiceSource.TEXT,
) -> InvoiceView:
    """The official XML (DIAN or CFDI), read by code. A hostile or foreign XML is refused before anything is stored."""
    if len(data) > MAX_DOCUMENT_BYTES:
        raise PayloadTooLarge()
    document_id = new_id()
    try:
        extraction = ctx.lanes.read_einvoice(
            data, document_id=document_id, company_name=workspace.company_name, source=source
        )
    except ExtractionError as error:
        raise EInvoiceRejected(f"No pudimos leer la factura electrónica: {error}") from error
    document = _store_document(
        ctx, workspace.id, data, filename=filename, media_type=XML_MEDIA_TYPE, document_id=document_id
    )
    return _receive(ctx, workspace, document, lambda: extraction, source=source, visible_text="")


def process_pending(ctx: ServiceContext, workspace: WorkspaceRow) -> Outcome:
    return decide(ctx, workspace, records.pending_invoices(ctx, workspace.id), execute_payments=True)


def decide(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    invoices: Sequence[InvoiceRow],
    approvals: Mapping[str, Approval] | None = None,
    *,
    execute_payments: bool = False,
    approval_context: Mapping[str, Any] | None = None,
) -> Outcome:
    """`execute_payments` is for the panel only: the firewall, the challenge and the red team decide, never pay.

    `approval_context` adds to each approval's ledger entry how it was given (e.g. once, or updating the agreement).
    """
    cases = [records.as_case(row) for row in invoices]
    policy = policy_service.current(ctx, workspace.id)
    learns = workspace.kind in VISITOR_KINDS  # sandboxes neither earn nor lose a supplier's trust
    state = records.company_state(ctx, workspace)
    if learns:
        state = trust_service.with_trust(ctx, workspace.id, state, policy)
    batch = ctx.lanes.decide_all(cases, state, policy, approvals)
    report = ctx.lanes.audit(batch, cases, state, policy)
    stopped = _stopped_payments(batch, report)
    final = _attach_approvals(_apply_stops(batch, stopped), approvals or {})

    rows = {row.id: row for row in invoices}

    def pay(decision: Decision) -> Payout:
        """Now if its day has come; otherwise the calendar sends it on the day it is scheduled for."""
        planned = schedule_service.timing(ctx, decision, rows[decision.invoice_id], policy)
        if planned.pay_on is not None and planned.pay_on > ctx.now().date():
            return None, {schedule_service.SCHEDULED_FOR: planned.pay_on.isoformat()}
        execution = payment_service.execute(ctx, workspace.id, schedule_service.for_rail(decision, planned), policy)
        return execution, {"timing": planned.timing.value, "discount_base": str(planned.discount_base)}

    payer = pay if execute_payments and payment_service.may_execute(workspace) else None
    # An intent is paid by the agent that sent it, even after a person approves it here: paying it too pays it twice.
    intents = {case.id for case in cases if case.extraction.source is InvoiceSource.INTENT}
    recorded = [
        _record(
            ctx,
            workspace.id,
            d,
            (approvals or {}).get(d.invoice_id),
            d.invoice_id in stopped,
            None if d.invoice_id in intents else payer,
            {"policy_version": policy.version, **(approval_context or {})},
        )
        for d in final.decisions
    ]
    for recorded_decision in recorded if learns else []:
        trust_service.learn(ctx, workspace.id, recorded_decision, policy)
    return Outcome(batch=final.model_copy(update={"decisions": recorded}), audit=report, vetoed=sorted(stopped))


def narrate(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> str:
    try:
        return ctx.lanes.narrate(records.decision(ctx, workspace_id, invoice_id))
    except LLMError as error:
        raise model_failure(error) from error


def view(row: InvoiceRow, *, decided: bool) -> InvoiceView:
    return InvoiceView(
        id=row.id,
        received_at=row.received_at,
        document_id=row.document_id,
        status="decided" if decided else "received",
        read_ok=row.read_ok,
        extraction=ExtractedInvoice.model_validate(row.extraction),
    )


def _receive(
    ctx: ServiceContext,
    workspace: WorkspaceRow,
    document: DocumentRow,
    read: Callable[[], ExtractedInvoice],
    *,
    source: InvoiceSource,
    visible_text: str,
) -> InvoiceView:
    try:
        extraction, read_ok = read(), True
    except LLMNotConfigured as error:
        raise ModelNotConfigured() from error  # a missing key is a setting to fix, not a document to review
    except LLMError:
        # Kept unread on purpose: R1 escalates it, so a person reviews it instead of anyone guessing.
        extraction, read_ok = _unread(document.id, source, visible_text), False
    partner = _same_invoice_pending(ctx, workspace.id, extraction) if read_ok else None
    if partner is not None:
        return _pair(ctx, workspace.id, partner, document, extraction)
    case = InvoiceCase(id=_new_invoice_id(), received_at=ctx.now(), extraction=extraction)
    row = records.store_invoice(ctx, workspace.id, case, document_id=document.id, read_ok=read_ok)
    payload = {**received_payload(case, document.id), "read": read_ok}
    ledger_service.append(ctx, workspace.id, LedgerKind.INVOICE_RECEIVED, case.id, payload)
    return view(row, decided=False)


def _same_invoice_pending(ctx: ServiceContext, workspace_id: str, reading: ExtractedInvoice) -> InvoiceRow | None:
    """The undecided invoice that is this one in its other form: its official XML, or its PDF or image."""
    for row in records.pending_invoices(ctx, workspace_id):
        other = ExtractedInvoice.model_validate(row.extraction)
        if is_einvoice_reading(other) == is_einvoice_reading(reading):
            continue
        official, document = (other, reading) if is_einvoice_reading(other) else (reading, other)
        if same_invoice(official, document):
            return row
    return None


def _pair(
    ctx: ServiceContext, workspace_id: str, row: InvoiceRow, document: DocumentRow, reading: ExtractedInvoice
) -> InvoiceView:
    """One invoice, not two: the XML's values stand and the other document fills only what the XML lacks."""
    stored = ExtractedInvoice.model_validate(row.extraction)
    official, other = (stored, reading) if is_einvoice_reading(stored) else (reading, stored)
    merged = merge(official, other)
    row.extraction = merged.model_dump(mode="json")
    ctx.session.flush()
    case = records.as_case(row)
    payload = {**received_payload(case, document.id), "read": True, "paired_with": row.document_id}
    ledger_service.append(ctx, workspace_id, LedgerKind.INVOICE_RECEIVED, row.id, payload)
    return view(row, decided=False)


def _store_document(
    ctx: ServiceContext,
    workspace_id: str,
    data: bytes,
    *,
    filename: str,
    media_type: str,
    document_id: str | None = None,
) -> DocumentRow:
    document = DocumentRow(
        id=document_id or new_id(),
        workspace_id=workspace_id,
        filename=filename[:255],
        media_type=media_type,
        data=data,
        created_at=ctx.now(),
    )
    ctx.session.add(document)
    ctx.session.flush()
    return document


def _unread(document_id: str, source: InvoiceSource, visible_text: str) -> ExtractedInvoice:
    unread = ExtractedField(value=None, confidence=0.0, verified=False)
    return ExtractedInvoice(
        document_id=document_id,
        source=source,
        visible_text=visible_text,
        sender_email=first_email(visible_text),
        reader=UNREAD_READER,
        overall_confidence=0.0,
        **dict.fromkeys(FIELD_NAMES, unread),
    )


def _stopped_payments(batch: BatchResult, report: AuditReport) -> dict[str, str]:
    """Payments that do not go out, with the reason the acta shows.

    The auditor's rejections win; if it cannot say which payment it rejects, or objects to the batch as a whole (a
    critical finding on no payment of the batch, e.g. the reserve), none of the batch's payments go out. As a last guard
    of the invariant, a payment whose own acta shows a failing hold rule never goes out either.
    """
    paid = [d for d in batch.decisions if d.status in records.PAID]
    paid_ids = {d.invoice_id for d in paid}
    critical = [f for f in report.findings if f.severity == "critical"]
    findings = {f.invoice_id: f.message for f in critical if f.invoice_id in paid_ids}
    on_the_batch = any(f.invoice_id not in paid_ids for f in critical)
    unattributed = on_the_batch or report.improper_payments > len(findings)
    stopped: dict[str, str] = {}
    for decision in paid:
        failing_holds = [r.label for r in decision.rules if r.outcome is RuleOutcome.HOLD]
        if decision.invoice_id in findings:
            stopped[decision.invoice_id] = f"{AUDITOR_STOP}: {findings[decision.invoice_id]}"
        elif unattributed:
            stopped[decision.invoice_id] = f"{AUDITOR_STOP}."
        elif failing_holds:
            stopped[decision.invoice_id] = f"{HOLD_RULE_STOP}: {', '.join(failing_holds)}."
    return stopped


def _apply_stops(batch: BatchResult, stopped: Mapping[str, str]) -> BatchResult:
    if not stopped:
        return batch
    held = [d for d in batch.decisions if d.invoice_id in stopped]
    decisions = [_held(d, stopped[d.invoice_id]) if d.invoice_id in stopped else d for d in batch.decisions]
    return batch.model_copy(
        update={
            "decisions": decisions,
            "balance_end": batch.balance_end + _total(held),
            "spent_auto_base": batch.spent_auto_base - _total(d for d in held if d.status is DecisionStatus.PAID_AUTO),
            "metrics": records.count_metrics(decisions, improper_payments=len(stopped)),
        }
    )


def _attach_approvals(batch: BatchResult, approvals: Mapping[str, Approval]) -> BatchResult:
    if not approvals:
        return batch
    decisions = [
        _with_approval(d, approvals[d.invoice_id]) if d.invoice_id in approvals else d for d in batch.decisions
    ]
    return batch.model_copy(update={"decisions": decisions})


def _with_approval(decision: Decision, approval: Approval) -> Decision:
    """The acta always shows who approved, and says plainly when an approval did not turn into a payment."""
    update: dict[str, Any] = {"approval": decision.approval or approval}
    unpaid = approval.decision == "approved" and decision.status not in records.PAID
    if unpaid and not decision.blocked_reason:
        update["blocked_reason"] = f"{approval.approver} la aprobó, pero no se pagó: {decision.explanation}"
    return decision.model_copy(update=update)


def _held(decision: Decision, reason: str) -> Decision:
    return decision.model_copy(
        update={"status": DecisionStatus.HOLD, "balance_after": decision.balance_before, "blocked_reason": reason}
    )


def _record(
    ctx: ServiceContext,
    workspace_id: str,
    decision: Decision,
    approval: Approval | None,
    audit_blocked: bool,
    pay: Callable[[Decision], Payout] | None,
    context: Mapping[str, Any],
) -> Decision:
    """The decision enters the ledger before any payment: the receipt the rail's guard asks for points to it."""
    kind = LedgerKind.APPROVAL if approval else LedgerKind.DECISION
    payload = _decision_payload(decision, audit_blocked)
    payload["policy_version"] = context["policy_version"]
    if approval:
        payload.update(context)
        payload["approval"] = approval.model_dump(mode="json")
    ledger_service.append(ctx, workspace_id, kind, decision.invoice_id, payload)
    payout: dict[str, Any] = {}
    if pay is not None and decision.status in records.PAID and not audit_blocked:
        execution, payout = pay(decision)
        if execution is not None:
            decision = decision.model_copy(update={"execution": execution})
    records.save_decision(ctx, workspace_id, decision, audit_blocked=audit_blocked)
    if decision.status in records.PAID:
        payment = {**payment_service.payment_payload(decision), **payout}
        ledger_service.append(ctx, workspace_id, LedgerKind.PAYMENT, decision.invoice_id, payment)
    return decision


def _decision_payload(decision: Decision, audit_blocked: bool) -> dict[str, Any]:
    failed = [r.rule_id for r in decision.rules if r.outcome in (RuleOutcome.HOLD, RuleOutcome.ESCALATE)]
    return {
        "status": decision.status.value,
        "agent_verdict": decision.agent_verdict.value,
        "amount_base": _number(decision.amount_base),
        "failed_rules": failed,
        "audit_blocked": audit_blocked,
        "beneficiary_id": decision.beneficiary_id,
        "amount": _number(decision.amount),
        "currency": decision.currency,
    }


def _number(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _total(decisions: Iterable[Decision]) -> Decimal:
    return sum((d.amount_base or Decimal(0) for d in decisions), Decimal(0))


def _new_invoice_id() -> str:
    return "INV-" + uuid.uuid4().hex[:12].upper()
