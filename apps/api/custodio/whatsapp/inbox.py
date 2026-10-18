"""Each WhatsApp message, start to end: claim it once, answer it, reply to the sender.

An invoice that arrives here takes the same path as an upload in the panel (read → decide → audit → ledger → pay if
the rules allow it). The text or caption of a message is data, never an instruction: a caption is not read at all, and
a text message is read as the invoice itself, so R2 escalates any instruction aimed at the agent. Nothing sent on
WhatsApp approves a payment: approvals happen only in the app.

Meta retries a delivery that was not answered with 200 in time, and Vercel may stop a function once it has answered,
so a message is processed inside its own request within a time budget. The message id is claimed in its own
transaction first: a retry that arrives meanwhile finds it claimed and is answered 200 at once; a claim left behind by
an instance that died is taken again after a while, up to a few attempts.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy.exc import IntegrityError

from custodio.contracts import InvoiceSource
from custodio.db.models import WhatsAppMessageRow, WorkspaceRow
from custodio.extraction.errors import ExtractionError
from custodio.services import invoice_service, rate_limits, records
from custodio.services.context import Runtime, ServiceContext
from custodio.services.errors import RateLimited, ServiceError
from custodio.services.invoice_service import InvoiceView
from custodio.whatsapp import linking, replies
from custodio.whatsapp.channel import WhatsAppChannel
from custodio.whatsapp.errors import (
    GraphUnavailable,
    LinkCodeExpired,
    LinkCodeInvalid,
    MediaRejected,
    WebhookSignatureInvalid,
)
from custodio.whatsapp.payload import InboundMessage, MediaRef, inbound_messages
from custodio.whatsapp.signature import signature_valid

STALE_CLAIM = timedelta(minutes=2)
MAX_ATTEMPTS = 3
MIN_INVOICE_TEXT_CHARS = 40  # "hola" or "¿ya pagaron?" is a chat, not an invoice: it gets help, not an acta
MEDIA_TIMEOUT_SECONDS = 15.0
MIN_TIMEOUT_SECONDS = 1.0
DEFAULT_FILENAMES = {"image": "whatsapp.jpg", "document": "whatsapp.pdf"}

logger = logging.getLogger(__name__)


class MessageStatus(StrEnum):
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True)
class Answer:
    reply: str | None
    workspace_id: str | None = None
    invoice_id: str | None = None


@dataclass
class Budget:
    seconds: float
    started: float = field(default_factory=time.monotonic)

    def remaining(self) -> float:
        return max(0.0, self.seconds - (time.monotonic() - self.started))

    def timeout(self, ceiling: float) -> float:
        return max(MIN_TIMEOUT_SECONDS, min(ceiling, self.remaining()))


class _Declined(Exception):
    """A message Blinka Keeper answers without reading an invoice: the reply says why."""

    def __init__(self, reply: str) -> None:
        super().__init__(reply)
        self.reply = reply


def receive_delivery(
    runtime: Runtime, channel: WhatsAppChannel, body: bytes, signature: str | None, base_url: str
) -> int:
    """Verifies the delivery before reading a byte of it; returns how many messages were for this number."""
    if not signature_valid(body, signature, channel.config.app_secret):
        raise WebhookSignatureInvalid()
    messages = inbound_messages(body, channel.config.phone_number_id)
    for message in messages:
        handle(runtime, channel, message, base_url)
    return len(messages)


def handle(runtime: Runtime, channel: WhatsAppChannel, message: InboundMessage, base_url: str) -> None:
    if not _claim(runtime, message.id):
        return
    try:
        answer = _answer(runtime, channel, message, base_url)
    except Exception as error:
        logger.warning("whatsapp message failed: %s", type(error).__name__)
        if not _release(runtime, message.id):
            raise  # Meta retries it
        answer = Answer(replies.UNAVAILABLE)
    if answer.reply:
        _reply(channel, message.sender, answer.reply)


def _answer(runtime: Runtime, channel: WhatsAppChannel, message: InboundMessage, base_url: str) -> Answer:
    try:
        rate_limits.check_whatsapp_message(runtime, phone=message.sender)
    except RateLimited:
        _finish_alone(runtime, message.id)
        return Answer(None)  # a flood gets no echo: answering it would feed it
    with runtime.database.session() as session:
        ctx = runtime.context(session)
        answer = _route(ctx, channel, message, Budget(channel.budget_seconds), base_url)
        _finish(ctx, message.id, answer)
    return answer


def _route(
    ctx: ServiceContext, channel: WhatsAppChannel, message: InboundMessage, budget: Budget, base_url: str
) -> Answer:
    text = message.text.body if message.text else ""
    code = linking.requested_code(text)
    if code is not None:
        return Answer(_link(ctx, message.sender, code))
    workspace = linking.workspace_of(ctx, message.sender)
    if workspace is None:
        return Answer(replies.UNLINKED)
    try:
        received = _receive(ctx, channel, message, workspace, budget)
    except _Declined as declined:
        return Answer(declined.reply, workspace.id)
    outcome = invoice_service.process_pending(ctx, workspace)
    decision = next(d for d in outcome.batch.decisions if d.invoice_id == received.id)
    acta = records.acta_url(ctx.runtime.public_base_url or base_url, received.id)
    reply = replies.decided(decision, received.extraction.invoice_number.value, acta)
    return Answer(reply, workspace.id, received.id)


def _link(ctx: ServiceContext, phone: str, code: str) -> str:
    try:
        rate_limits.check_whatsapp_link_attempt(ctx.runtime, phone=phone)
    except RateLimited:
        return replies.TOO_MANY_TRIES
    try:
        workspace = linking.redeem(ctx, phone, code)
    except LinkCodeExpired:
        return replies.CODE_EXPIRED
    except LinkCodeInvalid:
        return replies.CODE_INVALID
    return replies.linked(workspace.company_name)


def _receive(
    ctx: ServiceContext, channel: WhatsAppChannel, message: InboundMessage, workspace: WorkspaceRow, budget: Budget
) -> InvoiceView:
    if message.type == "text" and message.text is not None:
        return _receive_text(ctx, workspace, message.text.body)
    media = message.media
    if media is None:
        raise _Declined(replies.UNSUPPORTED)
    return _receive_media(ctx, channel, workspace, media, message.type, budget)


def _receive_text(ctx: ServiceContext, workspace: WorkspaceRow, text: str) -> InvoiceView:
    if len(text.strip()) < MIN_INVOICE_TEXT_CHARS:
        raise _Declined(replies.SEND_INVOICE)
    with _reading(ctx):
        return invoice_service.receive_text(ctx, workspace, text, source=InvoiceSource.WHATSAPP)


def _receive_media(
    ctx: ServiceContext, channel: WhatsAppChannel, workspace: WorkspaceRow, media: MediaRef, kind: str, budget: Budget
) -> InvoiceView:
    """The caption is never read: whatever it says, the invoice is only what the file shows."""
    try:
        file = channel.graph.fetch_media(media.id, timeout=budget.timeout(MEDIA_TIMEOUT_SECONDS))
    except MediaRejected as rejected:
        raise _Declined(replies.MEDIA_PROBLEMS[rejected.problem]) from rejected
    except GraphUnavailable as error:
        raise _Declined(replies.UNAVAILABLE) from error
    if budget.remaining() <= 0:
        raise _Declined(replies.UNAVAILABLE)
    filename = media.filename or DEFAULT_FILENAMES[kind]
    with _reading(ctx):
        return invoice_service.receive_document(
            ctx, workspace, file.data, filename=filename, media_type=file.media_type, source=InvoiceSource.WHATSAPP
        )


@contextmanager
def _reading(ctx: ServiceContext) -> Iterator[None]:
    """A reading that fails leaves nothing behind (no orphan document) and answers the sender instead."""
    savepoint = ctx.session.begin_nested()
    try:
        yield
    except (ServiceError, ExtractionError) as error:
        savepoint.rollback()
        raise _Declined(replies.UNREADABLE) from error
    except BaseException:
        savepoint.rollback()
        raise
    savepoint.commit()


def _claim(runtime: Runtime, message_id: str) -> bool:
    now = runtime.clock()
    try:
        with runtime.database.session() as session:
            row = session.get(WhatsAppMessageRow, message_id)
            if row is None:
                session.add(_new_claim(message_id, now))
                return True
            if not _retakeable(row, now):
                return False
            row.status, row.attempts, row.claimed_at = MessageStatus.PROCESSING.value, row.attempts + 1, now
            return True
    except IntegrityError:
        return False  # a retry claimed it at the same moment


def _new_claim(message_id: str, now: datetime) -> WhatsAppMessageRow:
    return WhatsAppMessageRow(
        message_id=message_id,
        workspace_id=None,
        status=MessageStatus.PROCESSING.value,
        attempts=1,
        invoice_id=None,
        claimed_at=now,
        finished_at=None,
    )


def _retakeable(row: WhatsAppMessageRow, now: datetime) -> bool:
    if row.attempts >= MAX_ATTEMPTS or row.status == MessageStatus.DONE.value:
        return False
    return row.status == MessageStatus.FAILED.value or row.claimed_at + STALE_CLAIM <= now


def _release(runtime: Runtime, message_id: str) -> bool:
    """Marks a failed attempt; True when it was the last one, so the sender is told instead of Meta retrying."""
    with runtime.database.session() as session:
        row = session.get(WhatsAppMessageRow, message_id)
        if row is None:
            return True
        last = row.attempts >= MAX_ATTEMPTS
        row.status = (MessageStatus.DONE if last else MessageStatus.FAILED).value
        row.finished_at = runtime.clock() if last else None
        return last


def _finish(ctx: ServiceContext, message_id: str, answer: Answer) -> None:
    row = ctx.session.get(WhatsAppMessageRow, message_id)
    if row is None:
        return
    row.status, row.finished_at = MessageStatus.DONE.value, ctx.now()
    row.workspace_id, row.invoice_id = answer.workspace_id, answer.invoice_id


def _finish_alone(runtime: Runtime, message_id: str) -> None:
    with runtime.database.session() as session:
        _finish(runtime.context(session), message_id, Answer(None))


def _reply(channel: WhatsAppChannel, to: str, body: str) -> None:
    try:
        channel.graph.send_text(to, body)
    except GraphUnavailable:
        logger.warning("whatsapp reply not sent")  # the invoice is in; the panel shows it either way
