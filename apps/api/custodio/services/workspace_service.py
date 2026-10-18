"""Workspaces: one per visitor (demo or blank), plus sandboxes for the public challenge and the red team."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select

from custodio.contracts import Amount, AuditReport, CompanyState, InvoiceCase, LedgerKind, Metrics, Policy
from custodio.corrections import demo as correction_demo
from custodio.db.models import WorkspaceRow
from custodio.services import ledger_service, policy_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import InvalidApiKey, WorkspaceNotFound

API_KEY_PREFIX = "cus_"
BLANK_COMPANY_NAME = "Mi empresa"


class WorkspaceMode(StrEnum):
    DEMO = "demo"
    BLANK = "blank"


class WorkspaceKind(StrEnum):
    DEMO = "demo"
    BLANK = "blank"
    CHALLENGE = "challenge"
    REDTEAM = "redteam"


VISITOR_KINDS = frozenset({WorkspaceKind.DEMO.value, WorkspaceKind.BLANK.value})


@dataclass(frozen=True)
class CreatedWorkspace:
    workspace_id: str
    api_key: str


class WorkspaceSummary(BaseModel):
    workspace_id: str
    mode: WorkspaceKind  # "demo" holds the example company; "blank" is a company of its own
    company_name: str
    today: date
    base_currency: str
    opening_balance: Amount
    balance: Amount
    spent_auto_base: Amount  # what the agent paid alone this calendar month, against `period_budget`
    reserve: Amount
    period_budget: Amount
    policy_version: int
    pending_invoices: int
    metrics: Metrics
    audit: AuditReport


def new_id() -> str:
    return uuid.uuid4().hex


def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def create(ctx: ServiceContext, mode: WorkspaceMode) -> CreatedWorkspace:
    if mode is WorkspaceMode.BLANK:
        return _create(ctx, WorkspaceKind.BLANK, *_blank_company(ctx.now().date()))
    state, policy = ctx.lanes.demo_company()
    created = _create(ctx, WorkspaceKind.DEMO, state, policy)
    _seed_invoices(ctx, created.workspace_id, ctx.lanes.demo_cases())
    _seed_invoices(ctx, created.workspace_id, correction_demo.seed_cases(policy, state.company_name))
    return created


def create_sandbox(ctx: ServiceContext, kind: WorkspaceKind, state: CompanyState, policy: Policy) -> str:
    """A workspace no visitor can open: the same company and rules, none of the invoices."""
    return _create(ctx, kind, state, policy).workspace_id


def get(ctx: ServiceContext, workspace_id: str) -> WorkspaceRow:
    row = ctx.session.get(WorkspaceRow, workspace_id)
    if row is None or row.kind not in VISITOR_KINDS:
        raise WorkspaceNotFound()
    return row


def get_sandbox(ctx: ServiceContext, workspace_id: str) -> WorkspaceRow:
    row = ctx.session.get(WorkspaceRow, workspace_id)
    if row is None:
        raise WorkspaceNotFound()
    return row


def by_api_key(ctx: ServiceContext, api_key: str) -> WorkspaceRow:
    row = ctx.session.scalars(select(WorkspaceRow).where(WorkspaceRow.api_key_hash == hash_secret(api_key))).first()
    if row is None or row.kind not in VISITOR_KINDS:
        raise InvalidApiKey()
    return row


def summary(ctx: ServiceContext, workspace: WorkspaceRow) -> WorkspaceSummary:
    policy = policy_service.current(ctx, workspace.id)
    return WorkspaceSummary(
        workspace_id=workspace.id,
        mode=WorkspaceKind(workspace.kind),
        company_name=workspace.company_name,
        today=ctx.now().date(),
        base_currency=policy.base_currency,
        opening_balance=workspace.opening_balance,
        balance=records.balance(ctx, workspace),
        spent_auto_base=records.autonomous_spend(ctx, workspace),
        reserve=policy.reserve,
        period_budget=policy.period_budget,
        policy_version=policy.version,
        pending_invoices=len(records.pending_invoices(ctx, workspace.id)),
        metrics=records.metrics(ctx, workspace.id),
        audit=records.audit_report(ctx, workspace.id),
    )


def update_company(
    ctx: ServiceContext, workspace: WorkspaceRow, *, name: str, opening_balance: Decimal, fx: dict[str, Decimal]
) -> None:
    workspace.company_name = name
    workspace.opening_balance = opening_balance
    workspace.fx_units_per_base = {currency: str(units) for currency, units in fx.items()}
    ctx.session.flush()


def _create(ctx: ServiceContext, kind: WorkspaceKind, state: CompanyState, policy: Policy) -> CreatedWorkspace:
    api_key = API_KEY_PREFIX + secrets.token_urlsafe(32)
    row = WorkspaceRow(
        id=new_id(),
        kind=kind.value,
        api_key_hash=hash_secret(api_key),
        company_name=state.company_name,
        opening_balance=state.opening_balance,
        fx_units_per_base={currency: str(units) for currency, units in state.fx_units_per_base.items()},
        history_seed=[record.model_dump(mode="json") for record in state.history],
        created_at=ctx.now(),
    )
    ctx.session.add(row)
    ctx.session.flush()
    policy_service.store(ctx, row.id, policy.model_copy(update={"version": 1}))
    return CreatedWorkspace(workspace_id=row.id, api_key=api_key)


def _seed_invoices(ctx: ServiceContext, workspace_id: str, cases: list[InvoiceCase]) -> None:
    for case in cases:
        records.store_invoice(ctx, workspace_id, case, document_id=None, read_ok=True)
        ledger_service.append(ctx, workspace_id, LedgerKind.INVOICE_RECEIVED, case.id, received_payload(case))


def received_payload(case: InvoiceCase, document_id: str | None = None) -> dict[str, Any]:
    reading = case.extraction
    return {
        "source": reading.source.value,
        "document_id": document_id,
        "supplier": reading.supplier_name.value,
        "invoice_number": reading.invoice_number.value,
        "amount": reading.amount.value,
        "currency": reading.currency.value,
        "reader": reading.reader,
    }


def _blank_company(today: date) -> tuple[CompanyState, Policy]:
    policy = Policy()
    state = CompanyState(
        workspace_id="blank",
        company_name=BLANK_COMPANY_NAME,
        today=today,
        opening_balance=Decimal(0),
        fx_units_per_base={policy.base_currency: Decimal(1)},
    )
    return state, policy
