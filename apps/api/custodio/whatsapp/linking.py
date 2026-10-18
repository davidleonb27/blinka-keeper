"""Ties a phone to one workspace with a short one-time code shown in the panel and sent from that phone.

The code expires, works once and only its digest is stored; each wrong try counts against the phone, so guessing a
code is out of reach. A phone belongs to one workspace at a time: linking it again moves it, never shares it.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from custodio.db.models import WhatsAppLinkCodeRow, WhatsAppPhoneRow, WorkspaceRow
from custodio.services.context import ServiceContext
from custodio.whatsapp.errors import LinkCodeExpired, LinkCodeInvalid

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0 or 1: nothing to misread on a projector
CODE_LENGTH = 6
CODE_TTL = timedelta(minutes=10)
LINK_WORD = "Vincular"
LINK_REQUEST = re.compile(rf"^\s*{LINK_WORD}\s+([A-Za-z0-9]{{{CODE_LENGTH}}})\s*$", re.IGNORECASE)
VISIBLE_DIGITS = 4
COUNTRY_DIGITS = 2
MASK = "•••"


@dataclass(frozen=True)
class LinkCode:
    code: str
    expires_at: datetime


def issue_code(ctx: ServiceContext, workspace_id: str) -> LinkCode:
    now = ctx.now()
    ctx.session.execute(delete(WhatsAppLinkCodeRow).where(WhatsAppLinkCodeRow.expires_at <= now))
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    expires_at = now + CODE_TTL
    ctx.session.add(
        WhatsAppLinkCodeRow(
            code_hash=_digest(code), workspace_id=workspace_id, created_at=now, expires_at=expires_at, used_at=None
        )
    )
    ctx.session.flush()
    return LinkCode(code=code, expires_at=expires_at)


def link_text(code: str) -> str:
    return f"{LINK_WORD} {code}"


def requested_code(text: str) -> str | None:
    match = LINK_REQUEST.match(text)
    return match.group(1).upper() if match else None


def redeem(ctx: ServiceContext, phone: str, code: str) -> WorkspaceRow:
    row = ctx.session.get(WhatsAppLinkCodeRow, _digest(code))
    if row is None or row.used_at is not None:
        raise LinkCodeInvalid()
    now = ctx.now()
    if row.expires_at <= now:
        raise LinkCodeExpired()
    row.used_at = now
    _link(ctx, phone, row.workspace_id, now)
    workspace = ctx.session.get(WorkspaceRow, row.workspace_id)
    if workspace is None:  # the cascade removes a deleted workspace's codes; this is the invariant, said aloud
        raise LinkCodeInvalid()
    return workspace


def workspace_of(ctx: ServiceContext, phone: str) -> WorkspaceRow | None:
    linked = ctx.session.get(WhatsAppPhoneRow, phone)
    return None if linked is None else ctx.session.get(WorkspaceRow, linked.workspace_id)


def phones_of(ctx: ServiceContext, workspace_id: str) -> list[WhatsAppPhoneRow]:
    query = select(WhatsAppPhoneRow).where(WhatsAppPhoneRow.workspace_id == workspace_id)
    return list(ctx.session.scalars(query.order_by(WhatsAppPhoneRow.linked_at)))


def mask(phone: str) -> str:
    """Enough to recognise one's own number, not enough to dial it: `+57 ••• 4567`."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) <= VISIBLE_DIGITS + COUNTRY_DIGITS:
        return f"{MASK} {digits[-VISIBLE_DIGITS:]}"
    return f"+{digits[:COUNTRY_DIGITS]} {MASK} {digits[-VISIBLE_DIGITS:]}"


def _link(ctx: ServiceContext, phone: str, workspace_id: str, now: datetime) -> None:
    linked = ctx.session.get(WhatsAppPhoneRow, phone)
    if linked is None:
        ctx.session.add(WhatsAppPhoneRow(phone=phone, workspace_id=workspace_id, linked_at=now))
    else:
        linked.workspace_id, linked.linked_at = workspace_id, now
    ctx.session.flush()


def _digest(code: str) -> str:
    return hashlib.sha256(code.upper().encode()).hexdigest()
