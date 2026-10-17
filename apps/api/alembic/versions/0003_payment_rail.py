"""payment rail: Stripe test accounts and payment executions

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stripe_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("beneficiary_id", sa.String(length=64), nullable=False),
        sa.Column("name_key", sa.String(length=200), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stripe_accounts")),
        sa.UniqueConstraint("beneficiary_id", "name_key", name=op.f("uq_stripe_accounts_beneficiary_id_name_key")),
    )
    op.create_table(
        "payment_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("rail", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("dashboard_url", sa.String(length=255), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_payment_executions_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_executions")),
        sa.UniqueConstraint("workspace_id", "invoice_id", name=op.f("uq_payment_executions_workspace_id_invoice_id")),
    )
    op.create_index(op.f("ix_payment_executions_executed_at"), "payment_executions", ["executed_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_executions_executed_at"), table_name="payment_executions")
    op.drop_table("payment_executions")
    op.drop_table("stripe_accounts")
