"""supplier_corrections: requests to a supplier to correct a stopped invoice

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_corrections",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("root_invoice_id", sa.String(length=64), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("original_status", sa.String(length=32), nullable=False),
        sa.Column("assessment", sa.JSON(), nullable=False),
        sa.Column("message", sa.String(length=4000), nullable=False),
        sa.Column("channels", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("corrected_invoice_id", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("alert", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_supplier_corrections_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_corrections")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_supplier_corrections_token_hash")),
    )
    op.create_index(op.f("ix_supplier_corrections_workspace_id"), "supplier_corrections", ["workspace_id"])
    op.create_index(op.f("ix_supplier_corrections_invoice_id"), "supplier_corrections", ["invoice_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_corrections_invoice_id"), table_name="supplier_corrections")
    op.drop_index(op.f("ix_supplier_corrections_workspace_id"), table_name="supplier_corrections")
    op.drop_table("supplier_corrections")
