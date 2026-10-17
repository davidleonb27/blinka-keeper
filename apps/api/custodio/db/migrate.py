"""`python -m custodio.db.migrate`: bring DATABASE_URL to the latest schema before the server starts (containers)."""

from __future__ import annotations

from custodio.config import get_settings
from custodio.db.database import Database


def main() -> None:
    Database(get_settings().database_url).migrate()


if __name__ == "__main__":
    main()
