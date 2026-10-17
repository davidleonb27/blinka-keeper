"""Tables. Portable types only (JSON, LargeBinary, Numeric(18,2)) so SQLite and Postgres share one schema."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

ID = String(64)
HASH = String(64)
MONEY = Numeric(18, 2)

NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UTCDateTime(TypeDecorator[datetime]):
    """Stores UTC and always returns aware UTC datetimes, whatever the backend does with time zones."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetimes are not stored")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map: ClassVar[dict[Any, Any]] = {datetime: UTCDateTime(), dict[str, Any]: JSON, list[Any]: JSON}


class WorkspaceRow(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    api_key_hash: Mapped[str] = mapped_column(HASH, unique=True)
    company_name: Mapped[str] = mapped_column(String(200))
    opening_balance: Mapped[Decimal] = mapped_column(MONEY)
    fx_units_per_base: Mapped[dict[str, Any]]
    history_seed: Mapped[list[Any]]
    created_at: Mapped[datetime]


class PolicyRow(Base):
    __tablename__ = "policies"
    __table_args__ = (UniqueConstraint("workspace_id", "version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    version: Mapped[int]
    document: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime]


class InvoiceRow(Base):
    __tablename__ = "invoices"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(ID, primary_key=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    received_at: Mapped[datetime]
    extraction: Mapped[dict[str, Any]]
    read_ok: Mapped[bool]
    expected: Mapped[str | None] = mapped_column(String(16))
    trap: Mapped[str | None] = mapped_column(String(200))


class DecisionRow(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "invoice_id"], ["invoices.workspace_id", "invoices.id"], ondelete="CASCADE"
        ),
    )

    workspace_id: Mapped[str] = mapped_column(ID, primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ID, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    document: Mapped[dict[str, Any]]
    audit_blocked: Mapped[bool]
    decided_at: Mapped[datetime]


class ApprovalRow(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    invoice_id: Mapped[str] = mapped_column(ID)
    decision: Mapped[str] = mapped_column(String(16))
    approver: Mapped[str] = mapped_column(String(120))
    channel: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(500))
    at: Mapped[datetime]


class LedgerEntryRow(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (UniqueConstraint("workspace_id", "seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int]
    at: Mapped[datetime]
    kind: Mapped[str] = mapped_column(String(32))
    subject_id: Mapped[str | None] = mapped_column(ID)
    payload: Mapped[dict[str, Any]]
    prev_hash: Mapped[str] = mapped_column(HASH)
    hash: Mapped[str] = mapped_column(HASH)


class ChallengeAttemptRow(Base):
    __tablename__ = "challenge_attempts"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    alias: Mapped[str | None] = mapped_column(String(60))
    technique: Mapped[str | None] = mapped_column(String(120))
    creativity: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(32), index=True)
    broke_through: Mapped[bool]
    decision: Mapped[dict[str, Any]]
    at: Mapped[datetime] = mapped_column(index=True)


class RedTeamRunRow(Base):
    __tablename__ = "redteam_runs"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    sandbox_workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    rounds: Mapped[int]
    attacks: Mapped[int]
    caught: Mapped[int]
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]


class RateCounterRow(Base):
    __tablename__ = "rate_counters"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    window_start: Mapped[int] = mapped_column(Integer, primary_key=True)
    count: Mapped[int]


class StripeAccountRow(Base):
    """Global on purpose: every demo workspace pays the same suppliers, so each gets one Stripe test account."""

    __tablename__ = "stripe_accounts"
    __table_args__ = (UniqueConstraint("beneficiary_id", "name_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    beneficiary_id: Mapped[str] = mapped_column(ID)
    name_key: Mapped[str] = mapped_column(String(200))
    account_id: Mapped[str] = mapped_column(ID)
    created_at: Mapped[datetime]


class PaymentExecutionRow(Base):
    __tablename__ = "payment_executions"
    __table_args__ = (UniqueConstraint("workspace_id", "invoice_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    invoice_id: Mapped[str] = mapped_column(ID)
    rail: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    external_id: Mapped[str | None] = mapped_column(ID)
    dashboard_url: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(String(500))
    instruction: Mapped[dict[str, Any] | None]
    attempts: Mapped[int]
    executed_at: Mapped[datetime] = mapped_column(index=True)


class ReconciliationRow(Base):
    """A statement reconciled against the workspace's payments. The outcome is stored whole: it is the record."""

    __tablename__ = "reconciliations"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)
    source: Mapped[str] = mapped_column(String(16))
    filename: Mapped[str] = mapped_column(String(255))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    demo_shift_days: Mapped[int | None]
    statement: Mapped[dict[str, Any]]
    outcome: Mapped[dict[str, Any]]
    reviews: Mapped[list[Any]]
    ledger_seq: Mapped[int]
    created_at: Mapped[datetime]
