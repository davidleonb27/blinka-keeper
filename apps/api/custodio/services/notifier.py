"""Approval requests by Telegram. A failed notification never blocks a decision: the panel can always approve."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class ApprovalRequest:
    chat_id: str
    text: str
    approve_token: str
    reject_token: str


class Notifier(Protocol):
    def send_approval_request(self, request: ApprovalRequest) -> None: ...

    def answer_callback(self, callback_id: str, text: str) -> None: ...


class NotificationFailed(RuntimeError):
    pass


class SilentNotifier:
    """Used when no bot token is configured: approvals happen in the panel only."""

    def send_approval_request(self, request: ApprovalRequest) -> None:
        return None

    def answer_callback(self, callback_id: str, text: str) -> None:
        return None


class TelegramNotifier:
    def __init__(self, bot_token: str) -> None:
        self._base = f"{TELEGRAM_API}/bot{bot_token}"

    def send_approval_request(self, request: ApprovalRequest) -> None:
        keyboard = [
            [
                {"text": "Aprobar", "callback_data": request.approve_token},
                {"text": "Rechazar", "callback_data": request.reject_token},
            ]
        ]
        self._call(
            "sendMessage",
            {"chat_id": request.chat_id, "text": request.text, "reply_markup": {"inline_keyboard": keyboard}},
        )

    def answer_callback(self, callback_id: str, text: str) -> None:
        self._call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text, "show_alert": True})

    def _call(self, method: str, payload: dict[str, object]) -> None:
        try:
            response = httpx.post(f"{self._base}/{method}", json=payload, timeout=TELEGRAM_TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.HTTPError as error:
            # The URL embeds the bot token, so only the method and the error class are logged.
            raise NotificationFailed(f"Telegram {method} falló ({type(error).__name__}).") from None


def notifier_from_environment() -> Notifier:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    return TelegramNotifier(token) if token else SilentNotifier()
