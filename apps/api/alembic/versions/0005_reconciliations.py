"""reconciliations: bank statements reconciled against payments

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reconciliations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("demo_shift_days", sa.Integer(), nullable=True),
        sa.Column("statement", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("reviews", sa.JSON(), nullable=False),
        sa.Column("ledger_seq", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_reconciliations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_reconciliations_document_id_documents"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reconciliations")),
    )
    op.create_index(op.f("ix_reconciliations_workspace_id"), "reconciliations", ["workspace_id"])
    op.create_index(op.f("ix_reconciliations_period"), "reconciliations", ["period"])


def downgrade() -> None:
    op.drop_index(op.f("ix_reconciliations_period"), table_name="reconciliations")
    op.drop_index(op.f("ix_reconciliations_workspace_id"), table_name="reconciliations")
    op.drop_table("reconciliations")
