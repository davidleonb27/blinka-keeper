from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict

from custodio.api.deps import RuntimeDep, Services
from custodio.contracts import DecisionStatus
from custodio.services import approval_service
from custodio.services.errors import WebhookForbidden

router = APIRouter(prefix="/telegram", tags=["telegram"])

NOTHING_TO_DO = "Sin acción: sólo atendemos los botones de aprobar o rechazar."


class _Telegram(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Telegram adds fields over time; we read only what we use


class Chat(_Telegram):
    id: int


class CallbackMessage(_Telegram):
    chat: Chat


class CallbackQuery(_Telegram):
    id: str
    data: str | None = None
    message: CallbackMessage | None = None


class TelegramUpdate(_Telegram):
    update_id: int
    callback_query: CallbackQuery | None = None


class WebhookResult(BaseModel):
    handled: bool
    message: str
    status: DecisionStatus | None = None


@router.post("/webhook", response_model=WebhookResult)
def webhook(
    update: TelegramUpdate,
    ctx: Services,
    runtime: RuntimeDep,
    secret: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> WebhookResult:
    expected = runtime.telegram_webhook_secret
    if expected is None or not hmac.compare_digest((secret or "").encode(), expected.encode()):
        raise WebhookForbidden()
    press = update.callback_query
    if press is None or not press.data or press.message is None:
        return WebhookResult(handled=False, message=NOTHING_TO_DO)
    outcome = approval_service.press_button(
        ctx, callback_id=press.id, token=press.data, chat_id=str(press.message.chat.id)
    )
    return WebhookResult(handled=outcome.handled, message=outcome.message, status=outcome.status)
