from pathlib import Path

from sqlalchemy import create_engine, inspect

from custodio.db import Database

TABLES = {"whatsapp_link_codes", "whatsapp_phones", "whatsapp_messages"}


def test_upgrade_head_builds_the_whatsapp_tables(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'whatsapp.db'}"

    Database(url).migrate()

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())
