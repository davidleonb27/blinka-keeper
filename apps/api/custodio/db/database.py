"""Engine, sessions and migrations.

Production runs on Neon through its pooled endpoint, so the app keeps no pool of its own (NullPool). The first
request of each instance runs `alembic upgrade head`; on Postgres it does so under an advisory lock so that two
cold-starting instances never migrate at the same time.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, event, text
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry, NullPool

from alembic import command

API_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = API_ROOT / "alembic"
MIGRATION_LOCK_ID = 7_301_984_512  # arbitrary, fixed: the advisory lock every instance agrees on


class Database:
    def __init__(self, url: str, *, serverless: bool = False) -> None:
        self.url = self.normalize_url(url)
        self.engine = self._create_engine(self.url, serverless=serverless)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)
        self._migrated = False
        self._lock = threading.Lock()

    @staticmethod
    def normalize_url(url: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.engine.dialect.name == "sqlite"

    @contextmanager
    def session(self) -> Iterator[Session]:
        """One unit of work: commit on success, roll back on any error."""
        with self._sessions() as session:
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    def migrate(self) -> None:
        with self.engine.connect() as connection:
            if self.is_sqlite:
                self._upgrade(connection)
                return
            connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
            try:
                self._upgrade(connection)
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})
                connection.commit()

    def ensure_migrated(self) -> None:
        if self._migrated:
            return
        with self._lock:
            if not self._migrated:
                self.migrate()
                self._migrated = True

    @staticmethod
    def _upgrade(connection: Connection) -> None:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        connection.commit()

    @staticmethod
    def _create_engine(url: str, *, serverless: bool) -> Engine:
        if url.startswith("sqlite"):
            engine = create_engine(url, connect_args={"check_same_thread": False})
            event.listen(engine, "connect", _enable_sqlite_foreign_keys)
            return engine
        if serverless:
            return create_engine(url, poolclass=NullPool)
        return create_engine(url, pool_pre_ping=True)


def _enable_sqlite_foreign_keys(connection: DBAPIConnection, _: ConnectionPoolEntry) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
