"""WhatsApp: Meta's webhook (verification and deliveries) and the panel's card to link a phone.

The webhook routes stay out of the OpenAPI document: only Meta calls them, and a delivery without a valid
X-Hub-Signature-256 is refused before a byte of it is read.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse

from custodio.api.deps import CurrentWorkspace, RuntimeDep, Services
from custodio.services.context import Runtime
from custodio.services.errors import PayloadTooLarge
from custodio.whatsapp import card, inbox
from custodio.whatsapp.card import LinkCodeView, WhatsAppStatus
from custodio.whatsapp.channel import WhatsAppChannel
from custodio.whatsapp.errors import WebhookForbidden, WhatsAppNotConfigured
from custodio.whatsapp.signature import token_matches

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

SUBSCRIBE = "subscribe"
MAX_WEBHOOK_BYTES = 256 * 1024  # a delivery is JSON with ids; files are fetched apart, from the Graph API


@router.get("/webhook", include_in_schema=False, response_class=PlainTextResponse)
def verify_webhook(
    runtime: RuntimeDep,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str, Query(alias="hub.challenge", max_length=256)] = "",
) -> str:
    channel = _channel(runtime)
    if mode != SUBSCRIBE or not token_matches(token, channel.config.verify_token):
        raise WebhookForbidden()
    return challenge


@router.post("/webhook", include_in_schema=False)
async def receive_webhook(
    request: Request,
    runtime: RuntimeDep,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> dict[str, int]:
    channel = _channel(runtime)
    body = await request.body()
    if len(body) > MAX_WEBHOOK_BYTES:
        raise PayloadTooLarge("El cuerpo del webhook supera el máximo permitido.")
    base_url = str(request.base_url).rstrip("/")
    handled = await run_in_threadpool(inbox.receive_delivery, runtime, channel, body, x_hub_signature_256, base_url)
    return {"messages": handled}


@router.get("/link", response_model=WhatsAppStatus)
def read_link(ctx: Services, workspace: CurrentWorkspace) -> WhatsAppStatus:
    return card.status(ctx, workspace)


@router.post("/link-codes", status_code=201, response_model=LinkCodeView)
def create_link_code(ctx: Services, workspace: CurrentWorkspace) -> LinkCodeView:
    return card.new_code(ctx, workspace)


def _channel(runtime: Runtime) -> WhatsAppChannel:
    if runtime.whatsapp is None:
        raise WhatsAppNotConfigured()
    return runtime.whatsapp
