"""Free-form text to a linked phone, for any part of Blinka Keeper that has news about an invoice it received there.

Only inside WhatsApp's 24-hour customer-service window (the sender wrote first); outside it Meta refuses free text.
"""

from __future__ import annotations

from custodio.db.models import WorkspaceRow
from custodio.services.context import ServiceContext
from custodio.whatsapp import linking
from custodio.whatsapp.errors import PhoneNotLinked, WhatsAppNotConfigured


def send_text(ctx: ServiceContext, workspace: WorkspaceRow, phone: str, body: str) -> None:
    """Sends `body` to `phone` only if that phone is linked to `workspace`: one workspace never writes to another's.

    Raises WhatsAppNotConfigured, PhoneNotLinked, or GraphUnavailable when Meta does not take the message.
    """
    channel = ctx.runtime.whatsapp
    if channel is None:
        raise WhatsAppNotConfigured()
    linked = linking.workspace_of(ctx, phone)
    if linked is None or linked.id != workspace.id:
        raise PhoneNotLinked()
    channel.graph.send_text(phone, body)
