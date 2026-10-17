"""Adaptive onboarding: propose a profile, import suppliers, then set the company up and simulate its first week."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from custodio.contracts import (
    Amount,
    BatchResult,
    Beneficiary,
    CompanyProfile,
    Evidence,
    ExtractedField,
    ExtractedInvoice,
    InvoiceCase,
    InvoiceSource,
    Policy,
    Ratio,
    SupplierImport,
)
from custodio.db.models import WorkspaceRow
from custodio.llm import LLMError
from custodio.services import policy_service, records, workspace_service
from custodio.services.context import ServiceContext
from custodio.services.errors import ModelUnavailable, PayloadTooLarge
from custodio.services.invoice_service import MAX_DOCUMENT_BYTES
from custodio.services.workspace_service import WorkspaceSummary

SIMULATION_READER = "simulación"


class OnboardingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: CompanyProfile
    policy: Policy
    suppliers: list[Beneficiary] = []
    opening_balance: Amount
    fx_units_per_base: dict[str, Ratio] | None = None  # defaults to the base currency alone


class OnboardingResult(BaseModel):
    workspace: WorkspaceSummary
    first_week: BatchResult  # simulated: nothing here was paid or recorded as a payment


def propose_profile(
    ctx: ServiceContext, company_name: str, website: str | None, answers: Mapping[str, str]
) -> CompanyProfile:
    try:
        return ctx.lanes.profile_company(company_name, website, answers)
    except LLMError as error:
        raise ModelUnavailable() from error


def import_suppliers(ctx: ServiceContext, data: bytes, *, filename: str, media_type: str) -> SupplierImport:
    if len(data) > MAX_DOCUMENT_BYTES:
        raise PayloadTooLarge()
    try:
        return ctx.lanes.import_suppliers(data, filename=filename, media_type=media_type)
    except LLMError as error:
        raise ModelUnavailable() from error


def complete(ctx: ServiceContext, workspace: WorkspaceRow, request: OnboardingRequest) -> OnboardingResult:
    base = request.profile.base_currency
    policy = request.policy.model_copy(
        update={"base_currency": base, "beneficiaries": request.suppliers or request.policy.beneficiaries}
    )
    fx = request.fx_units_per_base or {base: Decimal(1)}
    company = {"name": request.profile.company_name, "opening_balance": str(request.opening_balance)}
    applied = policy_service.apply(ctx, workspace.id, policy, context={"company": company})
    workspace_service.update_company(
        ctx, workspace, name=request.profile.company_name, opening_balance=request.opening_balance, fx=fx
    )
    return OnboardingResult(
        workspace=workspace_service.summary(ctx, workspace), first_week=_simulate_first_week(ctx, workspace, applied)
    )


def _simulate_first_week(ctx: ServiceContext, workspace: WorkspaceRow, policy: Policy) -> BatchResult:
    """One invoice per supplier with an agreement, exactly as agreed, decided by the engine and never stored."""
    contracted = [b for b in policy.beneficiaries if b.agreement is not None]
    cases = [_agreed_invoice(ctx, beneficiary, day) for day, beneficiary in enumerate(contracted)]
    return ctx.lanes.decide_all(cases, records.company_state(ctx, workspace), policy)


def _agreed_invoice(ctx: ServiceContext, beneficiary: Beneficiary, day: int) -> InvoiceCase:
    assert beneficiary.agreement is not None
    received = ctx.now() + timedelta(days=day)
    values = {
        "supplier_name": beneficiary.name,
        "supplier_tax_id": beneficiary.tax_id,
        "invoice_number": f"SIM-{day + 1:03d}",
        "issue_date": received.date().isoformat(),
        "amount": f"{beneficiary.agreement.amount:.2f}",
        "currency": beneficiary.agreement.currency,
        "bank_name": beneficiary.bank_name,
        "account_number": beneficiary.account_number,
        "description": "Primera semana simulada",
    }
    fields = {name: _given(value) for name, value in values.items()}
    extraction = ExtractedInvoice(
        document_id=f"sim-{beneficiary.id}",
        source=InvoiceSource.TEXT,
        due_date=ExtractedField(value=None, confidence=0.0),
        visible_text="\n".join(values.values()),
        reader=SIMULATION_READER,
        overall_confidence=1.0,
        **fields,
    )
    return InvoiceCase(id=f"SIM-{day + 1:03d}", received_at=received, extraction=extraction)


def _given(value: str) -> ExtractedField:
    return ExtractedField(value=value, evidence=Evidence(quote=value), confidence=1.0, verified=True)
