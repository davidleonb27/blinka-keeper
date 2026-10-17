from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from custodio.db.models import StripeAccountRow
from custodio.payments.port import Clock


class StripeAccountTable:
    """The `stripe_accounts` table: one test account per beneficiary and spelling of its name, across workspaces."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def find(self, beneficiary_id: str, name_key: str) -> str | None:
        return self._session.scalars(
            select(StripeAccountRow.account_id).where(
                StripeAccountRow.beneficiary_id == beneficiary_id, StripeAccountRow.name_key == name_key
            )
        ).first()

    def remember(self, beneficiary_id: str, name_key: str, account_id: str) -> str:
        # Two payments to a new beneficiary at once both create an account; the first stored is the one used.
        dialect = sqlite if self._session.get_bind().dialect.name == "sqlite" else postgresql
        statement = (
            dialect.insert(StripeAccountRow)
            .values(beneficiary_id=beneficiary_id, name_key=name_key, account_id=account_id, created_at=self._clock())
            .on_conflict_do_nothing(index_elements=["beneficiary_id", "name_key"])
        )
        self._session.execute(statement)
        return self.find(beneficiary_id, name_key) or account_id
