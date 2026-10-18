"""whatsapp: link codes, linked phones and delivered messages

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.schema import SchemaItem

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _workspace_key(table: str, *, nullable: bool = False) -> list[SchemaItem]:
    return [
        sa.Column("workspace_id", sa.String(length=64), nullable=nullable),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name=op.f(f"fk_{table}_workspace_id_workspaces"), ondelete="CASCADE"
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "whatsapp_link_codes",
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        *_workspace_key("whatsapp_link_codes"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("code_hash", name=op.f("pk_whatsapp_link_codes")),
    )
    op.create_table(
        "whatsapp_phones",
        sa.Column("phone", sa.String(length=32), nullable=False),
        *_workspace_key("whatsapp_phones"),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("phone", name=op.f("pk_whatsapp_phones")),
    )
    op.create_table(
        "whatsapp_messages",
        sa.Column("message_id", sa.String(length=255), nullable=False),
        *_workspace_key("whatsapp_messages", nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("message_id", name=op.f("pk_whatsapp_messages")),
    )
    for table in ("whatsapp_link_codes", "whatsapp_phones", "whatsapp_messages"):
        op.create_index(op.f(f"ix_{table}_workspace_id"), table, ["workspace_id"])


def downgrade() -> None:
    for table in ("whatsapp_messages", "whatsapp_phones", "whatsapp_link_codes"):
        op.drop_index(op.f(f"ix_{table}_workspace_id"), table_name=table)
        op.drop_table(table)
