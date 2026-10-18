"""Sends a correction request by WhatsApp when lane L20 is deployed and the flag is on. Copying the link always works.

Lane L20 exposes `send_text(workspace, phone, body)` in `custodio.whatsapp`; it is resolved on use so this lane works
before, and without, it. The message goes only to the phone registered for the supplier, never to a number a document
carries, and only for an invoice that arrived by WhatsApp.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
from collections.abc import Callable
from enum import StrEnum

from custodio.contracts import InvoiceSource
from custodio.db.models import WorkspaceRow

FLAG = "CUSTODIO_CORRECTIONS_WHATSAPP"
ENABLED_VALUES = frozenset({"1", "true", "on", "yes"})
WHATSAPP_MODULE = "custodio.whatsapp"
PHONE = re.compile(r"\+?\d[\d\s\-().]{6,}\d")

SendText = Callable[[WorkspaceRow, str, str], object]
logger = logging.getLogger(__name__)


class WhatsAppDelivery(StrEnum):
    SENT = "sent"
    OFF = "off"  # the flag is not on
    UNAVAILABLE = "unavailable"  # lane L20 is not deployed
    NOT_WHATSAPP = "not_whatsapp"  # the invoice did not arrive by WhatsApp
    NO_PHONE = "no_phone"  # the supplier has no registered phone
    FAILED = "failed"


def enabled() -> bool:
    return os.environ.get(FLAG, "").strip().lower() in ENABLED_VALUES


def whatsapp_sender() -> SendText | None:
    try:
        module = importlib.import_module(WHATSAPP_MODULE)
    except ImportError:
        return None
    sender: SendText | None = getattr(module, "send_text", None)
    return sender


def registered_phone(contact: str | None) -> str | None:
    found = PHONE.search(contact or "")
    if found is None:
        return None
    digits = re.sub(r"\D", "", found.group())
    return f"+{digits}"


def deliver(workspace: WorkspaceRow, source: InvoiceSource, contact: str | None, body: str) -> WhatsAppDelivery:
    if source is not InvoiceSource.WHATSAPP:
        return WhatsAppDelivery.NOT_WHATSAPP
    if not enabled():
        return WhatsAppDelivery.OFF
    send = whatsapp_sender()
    if send is None:
        return WhatsAppDelivery.UNAVAILABLE
    phone = registered_phone(contact)
    if phone is None:
        return WhatsAppDelivery.NO_PHONE
    try:
        send(workspace, phone, body)
    except Exception as error:  # another lane's transport: its failure must not undo the request
        logger.warning("whatsapp delivery failed: %s", type(error).__name__)
        return WhatsAppDelivery.FAILED
    return WhatsAppDelivery.SENT
