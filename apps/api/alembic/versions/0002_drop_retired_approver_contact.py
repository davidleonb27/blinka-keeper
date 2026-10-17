"""drop the retired messaging contact from stored approvers

Approvals are web only, so `Approver` lost its messaging chat id. Stored policies still carry the key and the
contract forbids unknown fields, so every policy document is rewritten without it.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RETIRED_KEY = "telegram_chat_id"
policies = sa.table("policies", sa.column("id", sa.Integer()), sa.column("document", sa.JSON()))


def upgrade() -> None:
    connection = op.get_bind()
    for row in connection.execute(sa.select(policies.c.id, policies.c.document)).all():
        approvers: list[dict[str, Any]] = row.document.get("approvers", [])
        if any(RETIRED_KEY in approver for approver in approvers):
            document = row.document | {"approvers": [_without_retired_key(a) for a in approvers]}
            connection.execute(policies.update().where(policies.c.id == row.id).values(document=document))


def downgrade() -> None:
    """Not reversible: the dropped values are not kept, and the older contract accepts their absence."""


def _without_retired_key(approver: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in approver.items() if key != RETIRED_KEY}
