from pathlib import Path

from sqlalchemy import create_engine, inspect

from custodio.db import Database

TABLES = {
    "workspaces",
    "policies",
    "documents",
    "invoices",
    "decisions",
    "approvals",
    "approval_tokens",
    "ledger_entries",
    "challenge_attempts",
    "redteam_runs",
    "rate_counters",
}


def test_upgrade_head_builds_every_table_on_an_empty_sqlite(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'empty.db'}"

    Database(url).migrate()

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())


def test_migrating_twice_is_harmless(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'twice.db'}")

    database.migrate()
    database.migrate()


def test_neon_urls_use_the_psycopg_driver() -> None:
    assert Database.normalize_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert Database.normalize_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert Database.normalize_url("sqlite:///x.db") == "sqlite:///x.db"
