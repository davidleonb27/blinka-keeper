"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_counters",
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("window_start", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key", "window_start", name=op.f("pk_rate_counters")),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("opening_balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("fx_units_per_base", sa.JSON(), nullable=False),
        sa.Column("history_seed", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
        sa.UniqueConstraint("api_key_hash", name=op.f("uq_workspaces_api_key_hash")),
    )
    op.create_table(
        "approval_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("approver", sa.String(length=120), nullable=False),
        sa.Column("chat_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_approval_tokens_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("token_hash", name=op.f("pk_approval_tokens")),
    )
    op.create_index(op.f("ix_approval_tokens_workspace_id"), "approval_tokens", ["workspace_id"])
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("approver", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name=op.f("fk_approvals_workspace_id_workspaces"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approvals")),
    )
    op.create_index(op.f("ix_approvals_workspace_id"), "approvals", ["workspace_id"])
    op.create_table(
        "challenge_attempts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("alias", sa.String(length=60), nullable=True),
        sa.Column("technique", sa.String(length=120), nullable=True),
        sa.Column("creativity", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("broke_through", sa.Boolean(), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_challenge_attempts_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_challenge_attempts")),
    )
    op.create_index(op.f("ix_challenge_attempts_at"), "challenge_attempts", ["at"])
    op.create_index(op.f("ix_challenge_attempts_status"), "challenge_attempts", ["status"])
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name=op.f("fk_documents_workspace_id_workspaces"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
    )
    op.create_index(op.f("ix_documents_workspace_id"), "documents", ["workspace_id"])
    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_ledger_entries_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
        sa.UniqueConstraint("workspace_id", "seq", name=op.f("uq_ledger_entries_workspace_id_seq")),
    )
    op.create_index(op.f("ix_ledger_entries_workspace_id"), "ledger_entries", ["workspace_id"])
    op.create_table(
        "policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name=op.f("fk_policies_workspace_id_workspaces"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policies")),
        sa.UniqueConstraint("workspace_id", "version", name=op.f("uq_policies_workspace_id_version")),
    )
    op.create_index(op.f("ix_policies_workspace_id"), "policies", ["workspace_id"])
    op.create_table(
        "redteam_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("sandbox_workspace_id", sa.String(length=64), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("attacks", sa.Integer(), nullable=False),
        sa.Column("caught", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["sandbox_workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_redteam_runs_sandbox_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_redteam_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_redteam_runs")),
    )
    op.create_index(op.f("ix_redteam_runs_workspace_id"), "redteam_runs", ["workspace_id"])
    op.create_table(
        "invoices",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extraction", sa.JSON(), nullable=False),
        sa.Column("read_ok", sa.Boolean(), nullable=False),
        sa.Column("expected", sa.String(length=16), nullable=True),
        sa.Column("trap", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name=op.f("fk_invoices_document_id_documents"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name=op.f("fk_invoices_workspace_id_workspaces"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("workspace_id", "id", name=op.f("pk_invoices")),
    )
    op.create_table(
        "decisions",
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("audit_blocked", sa.Boolean(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "invoice_id"],
            ["invoices.workspace_id", "invoices.id"],
            name=op.f("fk_decisions_workspace_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workspace_id", "invoice_id", name=op.f("pk_decisions")),
    )
    op.create_index(op.f("ix_decisions_status"), "decisions", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_decisions_status"), table_name="decisions")
    op.drop_table("decisions")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_redteam_runs_workspace_id"), table_name="redteam_runs")
    op.drop_table("redteam_runs")
    op.drop_index(op.f("ix_policies_workspace_id"), table_name="policies")
    op.drop_table("policies")
    op.drop_index(op.f("ix_ledger_entries_workspace_id"), table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(op.f("ix_documents_workspace_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index(op.f("ix_challenge_attempts_status"), table_name="challenge_attempts")
    op.drop_index(op.f("ix_challenge_attempts_at"), table_name="challenge_attempts")
    op.drop_table("challenge_attempts")
    op.drop_index(op.f("ix_approvals_workspace_id"), table_name="approvals")
    op.drop_table("approvals")
    op.drop_index(op.f("ix_approval_tokens_workspace_id"), table_name="approval_tokens")
    op.drop_table("approval_tokens")
    op.drop_table("workspaces")
    op.drop_table("rate_counters")
