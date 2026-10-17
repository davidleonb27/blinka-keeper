import json
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from custodio.config import get_settings
from custodio.contracts import Policy
from custodio.db import Database, migrate
from custodio.db.database import MIGRATIONS

TABLES = {
    "workspaces",
    "policies",
    "documents",
    "invoices",
    "decisions",
    "approvals",
    "ledger_entries",
    "challenge_attempts",
    "redteam_runs",
    "rate_counters",
    "stripe_accounts",
    "payment_executions",
}


def test_upgrade_head_builds_every_table_on_an_empty_sqlite(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'empty.db'}"

    Database(url).migrate()

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())


def test_migrating_twice_is_harmless(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'twice.db'}")

    database.migrate()
    database.migrate()


def test_upgrade_drops_the_retired_messaging_contact_from_stored_approvers(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(url)
    legacy = Policy().model_dump(mode="json") | {
        "approvers": [{"name": "Ana Gómez", "role": None, "telegram_chat_id": None, "email": None}]
    }
    with engine.begin() as connection:
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        connection.execute(
            text("INSERT INTO policies (workspace_id, version, document, created_at) VALUES ('w', 1, :doc, '2026')"),
            {"doc": json.dumps(legacy)},
        )

    Database(url).migrate()

    with engine.connect() as connection:
        stored = connection.execute(text("SELECT document FROM policies")).scalar_one()
    assert Policy.model_validate(json.loads(stored)).approvers[0].name == "Ana Gómez"


def test_neon_urls_use_the_psycopg_driver() -> None:
    assert Database.normalize_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert Database.normalize_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert Database.normalize_url("sqlite:///x.db") == "sqlite:///x.db"


def test_the_engine_talks_to_neon_through_psycopg() -> None:
    for url in ("postgres://u:p@host/db", "postgresql://u:p@host/db"):
        assert Database(url).engine.dialect.driver == "psycopg"


def test_the_container_entrypoint_migrates_the_configured_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'container.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    migrate.main()

    get_settings.cache_clear()
    assert TABLES <= set(inspect(create_engine(url)).get_table_names())
