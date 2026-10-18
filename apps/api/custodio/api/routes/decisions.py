from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from custodio.api.deps import CurrentWorkspace, ModelCallLimit, Services
from custodio.contracts import Decision, DecisionStatus, InvoiceSource, LedgerEntry
from custodio.receipts import DecisionReceipt
from custodio.services import (
    approval_service,
    invoice_service,
    ledger_service,
    payment_service,
    receipt_service,
    records,
)
from custodio.services.agreements import AgreementUpdate
from custodio.services.approval_service import AgreementPreview, ApprovedWithAgreement
from custodio.services.invoice_service import InvoiceView

router = APIRouter(prefix="/decisions", tags=["decisions"])

ApproverName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class ApprovalBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approver: ApproverName
    note: str | None = Field(default=None, max_length=500)


class ApproveOnceBody(BaseModel):
    """«Aprobar sólo esta vez»: the reason is mandatory and stays in the ledger."""

    model_config = ConfigDict(extra="forbid")

    approver: ApproverName
    reason: Reason


class AgreementBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(default=None, gt=0)  # the newly agreed amount, in the agreement's currency
    tolerance_pct: Decimal | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _changes_something(self) -> AgreementBody:
        if self.amount is None and self.tolerance_pct is None:
            raise ValueError("Indica el nuevo monto acordado o la nueva tolerancia.")
        return self

    def update(self) -> AgreementUpdate:
        return AgreementUpdate(amount=self.amount, tolerance_pct=self.tolerance_pct)


class ApproveWithAgreementBody(AgreementBody):
    """«Aprobar y actualizar el acuerdo», confirmed after seeing the simulation of `expected_policy_version`."""

    approver: ApproverName
    reason: Reason
    expected_policy_version: int = Field(ge=1)


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


@router.get("/{invoice_id}/receipt", response_model=DecisionReceipt)
def read_receipt(invoice_id: str, ctx: Services, workspace: CurrentWorkspace) -> DecisionReceipt:
    """The decision signed with Ed25519: anyone checks it with GET /.well-known/custodio-receipt-key."""
    return receipt_service.for_invoice(ctx, workspace.id, invoice_id)


@router.post("/{invoice_id}/approve", response_model=Decision)
def approve(invoice_id: str, body: ApprovalBody, ctx: Services, workspace: CurrentWorkspace) -> Decision:
    return approval_service.decide(ctx, workspace, invoice_id, "approved", approver=body.approver, note=body.note)


@router.post("/{invoice_id}/approve-once", response_model=Decision)
def approve_once(invoice_id: str, body: ApproveOnceBody, ctx: Services, workspace: CurrentWorkspace) -> Decision:
    """Pays this invoice only; the policy does not change."""
    return approval_service.approve_once(ctx, workspace, invoice_id, approver=body.approver, reason=body.reason)


@router.post("/{invoice_id}/agreement/preview", response_model=AgreementPreview)
def preview_agreement(
    invoice_id: str, body: AgreementBody, ctx: Services, workspace: CurrentWorkspace
) -> AgreementPreview:
    """Simulates the supplier's new agreement against everything received; changes nothing."""
    return approval_service.preview_agreement(ctx, workspace, invoice_id, body.update())


@router.post("/{invoice_id}/approve-with-agreement", response_model=ApprovedWithAgreement)
def approve_with_agreement(
    invoice_id: str, body: ApproveWithAgreementBody, ctx: Services, workspace: CurrentWorkspace
) -> ApprovedWithAgreement:
    return approval_service.approve_with_agreement(
        ctx,
        workspace,
        invoice_id,
        body.update(),
        approver=body.approver,
        reason=body.reason,
        simulated_on=body.expected_policy_version,
    )


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
