"""Point the Telegram bot at this deployment's webhook.

Usage (from apps/api): TELEGRAM_BOT_TOKEN=... uv run python -m scripts.set_telegram_webhook --url https://custodio.example

The secret Telegram echoes on every call is derived from the bot token, exactly as the API checks it, so no other
variable is needed. The token is read from the environment and never printed.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

from custodio.services.context import webhook_secret_for
from custodio.services.notifier import TELEGRAM_API, TELEGRAM_TIMEOUT_SECONDS

WEBHOOK_PATH = "/api/v1/telegram/webhook"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", required=True, help="public base URL of the deployment, e.g. https://custodio.app")
    args = parser.parse_args()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Falta TELEGRAM_BOT_TOKEN en el entorno.", file=sys.stderr)
        return 2
    response = httpx.post(
        f"{TELEGRAM_API}/bot{token}/setWebhook",
        json={
            "url": args.url.rstrip("/") + WEBHOOK_PATH,
            "secret_token": webhook_secret_for(token),
            "allowed_updates": ["callback_query"],
        },
        timeout=TELEGRAM_TIMEOUT_SECONDS,
    )
    print(response.json().get("description", response.status_code))
    return 0 if response.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
