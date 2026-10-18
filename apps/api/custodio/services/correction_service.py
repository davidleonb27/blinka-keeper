"""Supplier corrections: ask the supplier to fix a stopped invoice, then decide the fix with the same rules.

The request is offered only for causes a supplier can fix (`custodio.corrections.assess`); a changed account, a
duplicate, hidden instructions, an unregistered supplier or a sanctions match are never negotiated. The link is one
long random token (only its SHA-256 is stored) for one invoice, valid for EXPIRY and for one submission. What the
supplier sends goes down the single write path (`invoice_service`: reading, the fifteen rules, the independent auditor,
the ledger); the original stops being payable, so the same charge can never be paid twice. At most MAX_ROUNDS rounds.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import select, update

from custodio.contracts import (
    Amount,
    Beneficiary,
    Decision,
    DecisionStatus,
    ExtractedInvoice,
    InvoiceSource,
    LedgerKind,
)
from custodio.corrections import (
    Assessment,
    Blocker,
    BlockerKind,
    ConfirmationInvalid,
    CorrectableField,
    Issue,
    assess,
    compose_message,
    corrected_text,
    safe_reference,
)
from custodio.db.models import InvoiceRow, SupplierCorrectionRow, WorkspaceRow
from custodio.engine.beneficiaries import match_beneficiary
from custodio.services import invoice_service, ledger_service, policy_service, records, supplier_messaging
from custodio.services.context import ServiceContext
from custodio.services.errors import (
    CorrectionClosed,
    CorrectionInputInvalid,
    CorrectionLinkExpired,
    CorrectionLinkInvalid,
    CorrectionLinkUsed,
    CorrectionNotOffered,
    CorrectionOtherSupplier,
    UnsupportedMediaType,
)
from custodio.services.supplier_messaging import WhatsAppDelivery
from custodio.services.workspace_service import get as get_workspace
from custodio.services.workspace_service import new_id

EXPIRY = timedelta(days=7)
MAX_ROUNDS = 2
TOKEN_BYTES = 32  # 256 bits from secrets: not guessable, not derived from any id
SUPPLIER_PATH = "/proveedor/c/"
STOPPED = frozenset({DecisionStatus.HOLD, DecisionStatus.PENDING_APPROVAL})
PAID = frozenset({DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN})
SUPERSEDED = "Reemplazada por la corrección que envió el proveedor ({invoice_id}); esta versión ya no se paga."
RECEIPT = (
    "Recibimos su corrección. {company} la revisa con las mismas reglas de siempre; si falta algo, le escribirán de "
    "nuevo. Este enlace ya no sirve para otro envío."
)
ACCOUNT_ALERT = (
    "La corrección trae una cuenta distinta a la registrada: quedó frenada. Verifique el cambio con el contacto "
    "registrado del proveedor, nunca con un dato de la factura."
)
Receive = Callable[[WorkspaceRow, ExtractedInvoice], str]  # stores the corrected invoice, returns its id
BLOCKED_ALERT = "La corrección quedó frenada por una causa que no se negocia: {reasons}"


class CorrectionStatus(StrEnum):
    OPEN = "open"  # waiting for the supplier
    RECEIVED = "received"  # the supplier sent it and it was decided
    CLOSED = "closed"  # the invoice was resolved another way, or a newer link replaced this one
    EXPIRED = "expired"  # never stored: an open request past its expiry


class CorrectionRequest(BaseModel):
    id: str
    invoice_id: str
    root_invoice_id: str
    round: int
    status: CorrectionStatus
    issues: list[Issue]
    message: str
    channels: list[str]
    created_at: datetime
    expires_at: datetime
    submitted_at: datetime | None
    corrected_invoice_id: str | None
    outcome: DecisionStatus | None  # the corrected invoice's decision, as it stands now
    alert: str | None


class CorrectionOffer(BaseModel):
    invoice_id: str
    offered: bool
    reason: str | None  # Spanish, why it is not offered
    issues: list[Issue]
    blockers: list[Blocker]
    still_for_a_person: list[str]
    confirmable_fields: list[CorrectableField]
    next_round: int
    max_rounds: int
    open_request: CorrectionRequest | None
    history: list[CorrectionRequest]  # every round of this invoice's chain, oldest first


class CorrectionIssued(BaseModel):
    request: CorrectionRequest
    link: str  # shown once: only its hash is stored; asking again issues a new one and voids this
    message: str
    whatsapp: WhatsAppDelivery


class CorrectionOverview(BaseModel):
    requests: list[CorrectionRequest]
    requested: int
    waiting: int  # open, not expired
    resolved_with_supplier: int  # corrected and paid
    blocked_after_correction: int  # the correction brought a cause that is never negotiated


class SupplierIssue(BaseModel):
    problem: str
    expected: str
    fields: list[CorrectableField]


class SupplierCorrectionView(BaseModel):
    """All a supplier sees: this one invoice, what to fix and what is expected. Never a status or another invoice."""

    company_name: str
    supplier_name: str
    reference: str | None
    amount: Amount | None
    currency: str | None
    issues: list[SupplierIssue]
    fields: list[CorrectableField]
    confirmable: bool
    round: int
    max_rounds: int
    expires_at: datetime
    accepted_media_types: list[str]


class SupplierReceipt(BaseModel):
    received: bool
    message: str


# Company side -------------------------------------------------------------------------------------------------------


def offer(ctx: ServiceContext, workspace: WorkspaceRow, invoice_id: str) -> CorrectionOffer:
    decision = records.decision(ctx, workspace.id, invoice_id)
    row = records.invoice(ctx, workspace.id, invoice_id)
    assessment = _assess(ctx, workspace, decision, row)
    root, next_round = _chain_position(ctx, workspace.id, invoice_id)
    open_request = _open_request(ctx, workspace.id, invoice_id)
    reason = _why_not(ctx, workspace.id, decision, row, assessment, next_round)
    return CorrectionOffer(
        invoice_id=invoice_id,
        offered=reason is None,
        reason=reason,
        issues=assessment.issues,
        blockers=assessment.blockers,
        still_for_a_person=assessment.still_for_a_person,
        confirmable_fields=assessment.fields if assessment.confirmable else [],
        next_round=next_round,
        max_rounds=MAX_ROUNDS,
        open_request=_view(ctx, open_request) if open_request else None,
        history=[_view(ctx, request) for request in _chain(ctx, workspace.id, root)],
    )


def request(ctx: ServiceContext, workspace: WorkspaceRow, invoice_id: str, *, whatsapp: bool) -> CorrectionIssued:
    decision = records.decision(ctx, workspace.id, invoice_id)
    row = records.invoice(ctx, workspace.id, invoice_id)
    assessment = _assess(ctx, workspace, decision, row)
    root, next_round = _chain_position(ctx, workspace.id, invoice_id)
    reason = _why_not(ctx, workspace.id, decision, row, assessment, next_round)
    if reason is not None:
        raise CorrectionNotOffered(reason)
    token = secrets.token_urlsafe(TOKEN_BYTES)
    link = f"{ctx.runtime.public_base_url.rstrip('/')}{SUPPLIER_PATH}{token}"
    expires_at = ctx.now() + EXPIRY
    supplier = _supplier(ctx, workspace.id, decision)
    message = compose_message(
        company=workspace.company_name,
        supplier=supplier.name if supplier else "proveedor",
        reference=safe_reference(_extraction(row).invoice_number.value),
        issues=assessment.issues,
        link=link,
        expires_at=expires_at,
    )
    _close_open(ctx, workspace.id, invoice_id)  # a new link voids the previous one
    stored = _store(ctx, workspace.id, invoice_id, root, next_round, token, decision, assessment, message, expires_at)
    delivery = supplier_messaging.WhatsAppDelivery.OFF
    if whatsapp:
        source = _extraction(records.invoice(ctx, workspace.id, root)).source
        contact = supplier.approver_contact if supplier else None
        delivery = supplier_messaging.deliver(workspace, source, contact, message)
        if delivery is WhatsAppDelivery.SENT:
            stored.channels = [*stored.channels, "whatsapp"]
    ledger_service.append(
        ctx,
        workspace.id,
        LedgerKind.DECISION,
        invoice_id,
        {
            "event": "correction_requested",
            "request_id": stored.id,
            "round": next_round,
            "issues": [issue.kind.value for issue in assessment.issues],
            "expires_at": expires_at.isoformat(),
            "channels": stored.channels,
        },
    )
    ctx.session.flush()
    return CorrectionIssued(request=_view(ctx, stored), link=link, message=message, whatsapp=delivery)


def overview(ctx: ServiceContext, workspace: WorkspaceRow) -> CorrectionOverview:
    query = (
        select(SupplierCorrectionRow)
        .where(SupplierCorrectionRow.workspace_id == workspace.id)
        .order_by(SupplierCorrectionRow.created_at)
    )
    views = [_view(ctx, row) for row in ctx.session.scalars(query)]
    received = [view for view in views if view.status is CorrectionStatus.RECEIVED]
    return CorrectionOverview(
        requests=views,
        requested=len({view.root_invoice_id for view in views}),
        waiting=sum(view.status is CorrectionStatus.OPEN for view in views),
        resolved_with_supplier=sum(view.outcome in PAID for view in received),
        blocked_after_correction=sum(view.alert is not None for view in received),
    )


# Supplier side ------------------------------------------------------------------------------------------------------


def supplier_view(ctx: ServiceContext, token: str) -> SupplierCorrectionView:
    stored, workspace = _usable(ctx, token)
    decision = records.decision(ctx, workspace.id, stored.invoice_id)
    assessment = Assessment.model_validate(stored.assessment)
    supplier = _supplier(ctx, workspace.id, decision)
    reading = _extraction(records.invoice(ctx, workspace.id, stored.invoice_id))
    return SupplierCorrectionView(
        company_name=workspace.company_name,
        supplier_name=supplier.name if supplier else "proveedor",
        reference=safe_reference(reading.invoice_number.value),
        amount=decision.amount,
        currency=decision.currency,
        issues=[SupplierIssue(problem=i.problem, expected=i.expected, fields=i.fields) for i in assessment.issues],
        fields=assessment.fields if assessment.confirmable else [],
        confirmable=assessment.confirmable,
        round=stored.round,
        max_rounds=MAX_ROUNDS,
        expires_at=stored.expires_at,
        accepted_media_types=sorted(invoice_service.DOCUMENT_MEDIA_TYPES),
    )


def submit_document(ctx: ServiceContext, token: str, data: bytes, *, filename: str, media_type: str) -> SupplierReceipt:
    if media_type not in invoice_service.DOCUMENT_MEDIA_TYPES:
        raise UnsupportedMediaType()
    if not data:
        raise CorrectionInputInvalid()

    def receive(workspace: WorkspaceRow, _: ExtractedInvoice) -> str:
        return invoice_service.receive_document(ctx, workspace, data, filename=filename, media_type=media_type).id

    return _submit(ctx, token, receive)


def submit_confirmation(ctx: ServiceContext, token: str, values: Mapping[CorrectableField, str]) -> SupplierReceipt:
    stored, _ = _usable(ctx, token)
    assessment = Assessment.model_validate(stored.assessment)
    if not assessment.confirmable or set(values) != set(assessment.fields):
        raise CorrectionInputInvalid("Confirme exactamente los datos que se piden, o envíe la factura corregida.")

    def receive(workspace: WorkspaceRow, original: ExtractedInvoice) -> str:
        try:
            text = corrected_text(original, values)
        except ConfirmationInvalid as error:
            raise CorrectionInputInvalid(str(error)) from error
        return invoice_service.receive_text(ctx, workspace, text, source=InvoiceSource.TEXT).id

    return _submit(ctx, token, receive)


def _submit(ctx: ServiceContext, token: str, receive: Receive) -> SupplierReceipt:
    stored, workspace = _usable(ctx, token)
    original = _extraction(records.invoice(ctx, workspace.id, stored.invoice_id))
    corrected_id: str = receive(workspace, original)  # validates before anything is claimed
    corrected = records.invoice(ctx, workspace.id, corrected_id)
    _same_supplier(ctx, workspace.id, stored, corrected)
    _claim(ctx, stored)
    _claim_original(ctx, workspace.id, stored)
    decided = invoice_service.decide(ctx, workspace, [corrected], execute_payments=True).batch.decisions[0]
    _supersede(ctx, workspace.id, stored.invoice_id, corrected_id)
    stored.corrected_invoice_id = corrected_id
    stored.submitted_at = ctx.now()
    stored.outcome = decided.status.value
    stored.alert = _alert(ctx, workspace, decided, corrected)
    ledger_service.append(
        ctx,
        workspace.id,
        LedgerKind.DECISION,
        stored.invoice_id,
        {
            "event": "correction_received",
            "request_id": stored.id,
            "round": stored.round,
            "corrected_invoice_id": corrected_id,
            "corrected_status": decided.status.value,
            "alert": stored.alert,
        },
    )
    ctx.session.flush()
    return SupplierReceipt(received=True, message=RECEIPT.format(company=workspace.company_name))


# Rules of the offer -------------------------------------------------------------------------------------------------


def _why_not(
    ctx: ServiceContext,
    workspace_id: str,
    decision: Decision,
    row: InvoiceRow,
    assessment: Assessment,
    next_round: int,
) -> str | None:
    if _superseded(ctx, workspace_id, decision.invoice_id):
        return "Esta factura ya se reemplazó por la corrección del proveedor."
    if decision.status not in STOPPED or decision.approval is not None:
        return "Sólo se pide una corrección para una factura retenida o en espera que nadie haya decidido."
    if _extraction(row).source is InvoiceSource.INTENT:
        return "La pidió otro agente por el firewall: se corrige en el sistema que la envió, no con el proveedor."
    if assessment.blockers:
        return "Tiene causas que no se negocian con el proveedor; las revisa una persona."
    if not assessment.issues:
        return "No hay nada que el proveedor pueda corregir: lo que falta lo decide una persona de la empresa."
    if next_round > MAX_ROUNDS:
        return f"Ya hubo {MAX_ROUNDS} rondas de corrección con el proveedor; ahora decide una persona."
    return None


def _assess(ctx: ServiceContext, workspace: WorkspaceRow, decision: Decision, row: InvoiceRow) -> Assessment:
    policy = policy_service.current(ctx, workspace.id)
    return assess(decision, _extraction(row), policy, received_on=row.received_at.date())


def _chain_position(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> tuple[str, int]:
    """The chain's first invoice and the round a request for `invoice_id` would be."""
    parent = _received_for(ctx, workspace_id, invoice_id)
    if parent is None:
        return invoice_id, 1
    return parent.root_invoice_id, parent.round + 1


def _received_for(ctx: ServiceContext, workspace_id: str, corrected_id: str) -> SupplierCorrectionRow | None:
    query = select(SupplierCorrectionRow).where(
        SupplierCorrectionRow.workspace_id == workspace_id,
        SupplierCorrectionRow.corrected_invoice_id == corrected_id,
    )
    return ctx.session.scalars(query).first()


def _superseded(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> bool:
    query = select(SupplierCorrectionRow.id).where(
        SupplierCorrectionRow.workspace_id == workspace_id,
        SupplierCorrectionRow.invoice_id == invoice_id,
        SupplierCorrectionRow.status == CorrectionStatus.RECEIVED.value,
    )
    return ctx.session.scalars(query).first() is not None


def _chain(ctx: ServiceContext, workspace_id: str, root: str) -> list[SupplierCorrectionRow]:
    query = (
        select(SupplierCorrectionRow)
        .where(SupplierCorrectionRow.workspace_id == workspace_id, SupplierCorrectionRow.root_invoice_id == root)
        .order_by(SupplierCorrectionRow.created_at)
    )
    return list(ctx.session.scalars(query))


def _open_request(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> SupplierCorrectionRow | None:
    query = select(SupplierCorrectionRow).where(
        SupplierCorrectionRow.workspace_id == workspace_id,
        SupplierCorrectionRow.invoice_id == invoice_id,
        SupplierCorrectionRow.status == CorrectionStatus.OPEN.value,
    )
    found = ctx.session.scalars(query).first()
    return found if found is not None and found.expires_at > ctx.now() else None


def _close_open(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> None:
    ctx.session.execute(
        update(SupplierCorrectionRow)
        .where(
            SupplierCorrectionRow.workspace_id == workspace_id,
            SupplierCorrectionRow.invoice_id == invoice_id,
            SupplierCorrectionRow.status == CorrectionStatus.OPEN.value,
        )
        .values(status=CorrectionStatus.CLOSED.value)
    )


def _store(
    ctx: ServiceContext,
    workspace_id: str,
    invoice_id: str,
    root: str,
    round_number: int,
    token: str,
    decision: Decision,
    assessment: Assessment,
    message: str,
    expires_at: datetime,
) -> SupplierCorrectionRow:
    row = SupplierCorrectionRow(
        id=new_id(),
        workspace_id=workspace_id,
        invoice_id=invoice_id,
        root_invoice_id=root,
        round=round_number,
        token_hash=_hash(token),
        status=CorrectionStatus.OPEN.value,
        original_status=decision.status.value,
        assessment=assessment.model_dump(mode="json"),
        message=message,
        channels=["link"],
        created_at=ctx.now(),
        expires_at=expires_at,
    )
    ctx.session.add(row)
    ctx.session.flush()
    return row


# The link -----------------------------------------------------------------------------------------------------------


def _usable(ctx: ServiceContext, token: str) -> tuple[SupplierCorrectionRow, WorkspaceRow]:
    query = select(SupplierCorrectionRow).where(SupplierCorrectionRow.token_hash == _hash(token))
    stored = ctx.session.scalars(query).first()
    if stored is None:
        raise CorrectionLinkInvalid()
    if stored.status == CorrectionStatus.RECEIVED.value:
        raise CorrectionLinkUsed()
    if stored.status == CorrectionStatus.CLOSED.value:
        raise CorrectionClosed()
    if stored.expires_at <= ctx.now():
        raise CorrectionLinkExpired()
    workspace = get_workspace(ctx, stored.workspace_id)
    decision = records.decision(ctx, workspace.id, stored.invoice_id)
    if decision.status.value != stored.original_status or decision.approval is not None:
        raise CorrectionClosed()  # a person decided it meanwhile: the request is moot
    return stored, workspace


def _same_supplier(
    ctx: ServiceContext, workspace_id: str, stored: SupplierCorrectionRow, corrected: InvoiceRow
) -> None:
    """A link answers for one supplier's invoice: anything else is refused before it is decided, let alone paid."""
    expected = records.decision(ctx, workspace_id, stored.invoice_id).beneficiary_id
    reading = _extraction(corrected)
    found = match_beneficiary(
        policy_service.current(ctx, workspace_id),
        name=reading.supplier_name.value,
        tax_id=reading.supplier_tax_id.value,
    ).beneficiary
    if found is None or found.id != expected:
        raise CorrectionOtherSupplier()


def _claim(ctx: ServiceContext, stored: SupplierCorrectionRow) -> None:
    """Single use under concurrency: only the submission that flips the row from open wins."""
    claimed = ctx.session.execute(
        update(SupplierCorrectionRow)
        .where(SupplierCorrectionRow.id == stored.id, SupplierCorrectionRow.status == CorrectionStatus.OPEN.value)
        .values(status=CorrectionStatus.RECEIVED.value)
    )
    if claimed.rowcount != 1:  # type: ignore[attr-defined]
        raise CorrectionLinkUsed()
    ctx.session.refresh(stored)


def _claim_original(ctx: ServiceContext, workspace_id: str, stored: SupplierCorrectionRow) -> None:
    """A pending original is locked as an approval would lock it, so a person and the supplier cannot both pay it."""
    pending = stored.original_status == DecisionStatus.PENDING_APPROVAL.value
    if pending and not records.claim_pending(ctx, workspace_id, stored.invoice_id):
        raise CorrectionClosed()


def _supersede(ctx: ServiceContext, workspace_id: str, original_id: str, corrected_id: str) -> None:
    original = records.decision(ctx, workspace_id, original_id)
    status = DecisionStatus.REJECTED if original.status is DecisionStatus.PENDING_APPROVAL else original.status
    replaced = original.model_copy(
        update={"status": status, "blocked_reason": SUPERSEDED.format(invoice_id=corrected_id)}
    )
    records.save_decision(ctx, workspace_id, replaced, audit_blocked=False)


def _alert(ctx: ServiceContext, workspace: WorkspaceRow, decided: Decision, corrected: InvoiceRow) -> str | None:
    blockers = _assess(ctx, workspace, decided, corrected).blockers
    if not blockers:
        return None
    if any(blocker.kind is BlockerKind.ACCOUNT_CHANGED for blocker in blockers):
        return ACCOUNT_ALERT
    return BLOCKED_ALERT.format(reasons=" ".join(blocker.reason for blocker in blockers))[:500]


# Helpers ------------------------------------------------------------------------------------------------------------


def _view(ctx: ServiceContext, row: SupplierCorrectionRow) -> CorrectionRequest:
    status = CorrectionStatus(row.status)
    if status is CorrectionStatus.OPEN and row.expires_at <= ctx.now():
        status = CorrectionStatus.EXPIRED
    outcome = None
    if row.corrected_invoice_id is not None:
        outcome = records.decision(ctx, row.workspace_id, row.corrected_invoice_id).status
    return CorrectionRequest(
        id=row.id,
        invoice_id=row.invoice_id,
        root_invoice_id=row.root_invoice_id,
        round=row.round,
        status=status,
        issues=Assessment.model_validate(row.assessment).issues,
        message=row.message,
        channels=[str(channel) for channel in row.channels],
        created_at=row.created_at,
        expires_at=row.expires_at,
        submitted_at=row.submitted_at,
        corrected_invoice_id=row.corrected_invoice_id,
        outcome=outcome,
        alert=row.alert,
    )


def _supplier(ctx: ServiceContext, workspace_id: str, decision: Decision) -> Beneficiary | None:
    policy = policy_service.current(ctx, workspace_id)
    return next((b for b in policy.beneficiaries if b.id == decision.beneficiary_id), None)


def _extraction(row: InvoiceRow) -> ExtractedInvoice:
    return ExtractedInvoice.model_validate(row.extraction)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
