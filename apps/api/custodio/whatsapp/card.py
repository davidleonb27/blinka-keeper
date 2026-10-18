"""What the panel's «Recibe facturas por WhatsApp» card shows: whether the channel is on, the linked phones (masked)
and when the last invoice arrived, so the panel refreshes itself when one does."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from pydantic import BaseModel
from sqlalchemy import func, select

from custodio.db.models import WhatsAppMessageRow, WorkspaceRow
from custodio.services.context import ServiceContext
from custodio.whatsapp import linking
from custodio.whatsapp.channel import WhatsAppChannel
from custodio.whatsapp.errors import WhatsAppNotConfigured

WA_ME = "https://wa.me"


class LinkedPhone(BaseModel):
    masked: str  # never the full number
    linked_at: datetime


class WhatsAppStatus(BaseModel):
    enabled: bool
    display_number: str | None
    phones: list[LinkedPhone]
    last_received_at: datetime | None  # the last invoice this workspace received on WhatsApp


class LinkCodeView(BaseModel):
    code: str
    expires_at: datetime
    message: str  # the text to send, code included
    link_url: str  # wa.me link with the message filled in; the panel also draws it as a QR code
    display_number: str


def status(ctx: ServiceContext, workspace: WorkspaceRow) -> WhatsAppStatus:
    channel = ctx.runtime.whatsapp
    if channel is None or not channel.shows_card:
        return WhatsAppStatus(enabled=False, display_number=None, phones=[], last_received_at=None)
    rows = linking.phones_of(ctx, workspace.id)
    phones = [LinkedPhone(masked=linking.mask(row.phone), linked_at=row.linked_at) for row in rows]
    return WhatsAppStatus(
        enabled=True,
        display_number=channel.config.display_number,
        phones=phones,
        last_received_at=_last_invoice_at(ctx, workspace.id),
    )


def new_code(ctx: ServiceContext, workspace: WorkspaceRow) -> LinkCodeView:
    channel = _shown(ctx.runtime.whatsapp)
    issued = linking.issue_code(ctx, workspace.id)
    message = linking.link_text(issued.code)
    number = channel.config.display_number or ""
    return LinkCodeView(
        code=issued.code,
        expires_at=issued.expires_at,
        message=message,
        link_url=f"{WA_ME}/{number}?text={quote(message)}",
        display_number=number,
    )


def _shown(channel: WhatsAppChannel | None) -> WhatsAppChannel:
    if channel is None or not channel.shows_card:
        raise WhatsAppNotConfigured()
    return channel


def _last_invoice_at(ctx: ServiceContext, workspace_id: str) -> datetime | None:
    query = select(func.max(WhatsAppMessageRow.finished_at)).where(
        WhatsAppMessageRow.workspace_id == workspace_id, WhatsAppMessageRow.invoice_id.is_not(None)
    )
    return ctx.session.scalar(query)
