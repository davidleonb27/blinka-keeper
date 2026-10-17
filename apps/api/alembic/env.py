"""Runs migrations on the connection the app hands over, or on DATABASE_URL when called from the CLI."""

from __future__ import annotations

from sqlalchemy import Connection

from alembic import context
from custodio.config import get_settings
from custodio.db.database import Database
from custodio.db.models import Base


def run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


handed_over = context.config.attributes.get("connection")
if isinstance(handed_over, Connection):
    run(handed_over)
else:
    with Database(get_settings().database_url).engine.connect() as connection:
        run(connection)
        connection.commit()
