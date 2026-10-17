from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from custodio.api.deps import CurrentWorkspace, ModelCallLimit, Services
from custodio.contracts import Decision, DecisionStatus, InvoiceSource, LedgerEntry
from custodio.services import approval_service, invoice_service, ledger_service, payment_service, records
from custodio.services.invoice_service import InvoiceView

router = APIRouter(prefix="/decisions", tags=["decisions"])

ApproverName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ApprovalBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approver: ApproverName
    note: str | None = Field(default=None, max_length=500)


class DecisionItem(BaseModel):
    """A row of the panel: the decision plus when and through which channel its invoice arrived."""

    decision: Decision
    received_at: datetime
    source: InvoiceSource
    invoice_number: str | None  # as read from the invoice, for the panel's search and its CSV export


class Acta(BaseModel):
    decision: Decision
    invoice: InvoiceView
    ledger: list[LedgerEntry]


@router.get("", response_model=list[DecisionItem])
def list_decisions(
    ctx: Services, workspace: CurrentWorkspace, status: Annotated[DecisionStatus | None, Query()] = None
) -> list[DecisionItem]:
    return [
        DecisionItem(
            decision=decision,
            received_at=row.received_at,
            source=row.extraction["source"],
            invoice_number=row.extraction["invoice_number"]["value"],
        )
        for decision, row in records.decisions(ctx, workspace.id, status)
    ]


@router.get("/{invoice_id}", response_model=Acta)
def read_acta(invoice_id: str, ctx: Services, workspace: CurrentWorkspace) -> Acta:
    decision = records.decision(ctx, workspace.id, invoice_id)
    invoice = records.invoice(ctx, workspace.id, invoice_id)
    return Acta(
        decision=decision,
        invoice=invoice_service.view(invoice, decided=True),
        ledger=ledger_service.entries(ctx, workspace.id, subject_id=invoice_id),
    )


@router.post("/{invoice_id}/approve", response_model=Decision)
def approve(invoice_id: str, body: ApprovalBody, ctx: Services, workspace: CurrentWorkspace) -> Decision:
    return approval_service.decide(ctx, workspace, invoice_id, "approved", approver=body.approver, note=body.note)


@router.post("/{invoice_id}/reject", response_model=Decision)
def reject(invoice_id: str, body: ApprovalBody, ctx: Services, workspace: CurrentWorkspace) -> Decision:
    return approval_service.decide(ctx, workspace, invoice_id, "rejected", approver=body.approver, note=body.note)


@router.post("/{invoice_id}/execute", response_model=Decision)
def execute_payment(invoice_id: str, ctx: Services, workspace: CurrentWorkspace) -> Decision:
    """Retries a payment whose execution failed. A payment that already went out is returned unchanged."""
    return payment_service.retry(ctx, workspace, invoice_id)


class Narrative(BaseModel):
    invoice_id: str
    narrative: str


@router.get("/{invoice_id}/narrative", response_model=Narrative, dependencies=[ModelCallLimit])
def read_narrative(invoice_id: str, ctx: Services, workspace: CurrentWorkspace) -> Narrative:
    return Narrative(invoice_id=invoice_id, narrative=invoice_service.narrate(ctx, workspace.id, invoice_id))
