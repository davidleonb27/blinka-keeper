"""The chained ledger of each workspace. Hashing and verification belong to the engine; this module stores them."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from custodio.contracts import LedgerEntry, LedgerKind, LedgerVerification
from custodio.db.models import LedgerEntryRow
from custodio.services.context import ServiceContext
from custodio.services.errors import LedgerEntryNotFound

TAMPER_MARK = "alterado"
APPEND_ATTEMPTS = 5  # each retry re-reads the head another writer just committed; more than a few means a bug
_LOCK_CHAIN = text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))")


class TamperDemo(BaseModel):
    altered_seq: int
    altered_field: str
    tampered: LedgerVerification
    real: LedgerVerification


def append(
    ctx: ServiceContext, workspace_id: str, kind: LedgerKind, subject_id: str | None, payload: dict[str, Any]
) -> LedgerEntry:
    """Chains one entry. A concurrent writer may take the same seq first: retry on top of its committed head."""
    _lock_chain(ctx, workspace_id)
    for _ in range(APPEND_ATTEMPTS - 1):
        try:
            return _append_once(ctx, workspace_id, kind, subject_id, payload)
        except IntegrityError:
            continue
    return _append_once(ctx, workspace_id, kind, subject_id, payload)


def _lock_chain(ctx: ServiceContext, workspace_id: str) -> None:
    """Postgres: writers of one workspace take turns until they commit, so retries cannot run out under load.

    SQLite already serializes every writer, which leaves it only the retry.
    """
    if ctx.session.get_bind().dialect.name == "postgresql":
        ctx.session.execute(_LOCK_CHAIN, {"key": f"ledger:{workspace_id}"})


def _append_once(
    ctx: ServiceContext, workspace_id: str, kind: LedgerKind, subject_id: str | None, payload: dict[str, Any]
) -> LedgerEntry:
    entry = ctx.lanes.next_ledger_entry(
        _head(ctx, workspace_id), kind=kind, subject_id=subject_id, payload=payload, at=ctx.now()
    )
    with ctx.session.begin_nested():  # a savepoint: a collision rolls back this insert, not the caller's work
        ctx.session.add(_row(workspace_id, entry))
    return entry


def _row(workspace_id: str, entry: LedgerEntry) -> LedgerEntryRow:
    return LedgerEntryRow(
        workspace_id=workspace_id,
        seq=entry.seq,
        at=entry.at,
        kind=entry.kind.value,
        subject_id=entry.subject_id,
        payload=entry.payload,
        prev_hash=entry.prev_hash,
        hash=entry.hash,
    )


def entries(
    ctx: ServiceContext,
    workspace_id: str,
    subject_id: str | None = None,
    kinds: Sequence[LedgerKind] | None = None,
) -> list[LedgerEntry]:
    query = select(LedgerEntryRow).where(LedgerEntryRow.workspace_id == workspace_id)
    if subject_id is not None:
        query = query.where(LedgerEntryRow.subject_id == subject_id)
    if kinds is not None:
        query = query.where(LedgerEntryRow.kind.in_([kind.value for kind in kinds]))
    rows = ctx.session.scalars(query.order_by(LedgerEntryRow.seq))
    return [_entry(row) for row in rows]


def verify(ctx: ServiceContext, workspace_id: str) -> LedgerVerification:
    return ctx.lanes.verify_ledger(entries(ctx, workspace_id))


def tamper_demo(ctx: ServiceContext, workspace_id: str, seq: int | None) -> TamperDemo:
    """Alters one entry of an in-memory copy and verifies it. The stored ledger is only read."""
    chain = entries(ctx, workspace_id)
    target = seq if seq is not None else len(chain)
    if not 1 <= target <= len(chain):
        raise LedgerEntryNotFound()
    copy = [_tampered(entry) if entry.seq == target else entry for entry in chain]
    return TamperDemo(
        altered_seq=target,
        altered_field="payload",
        tampered=ctx.lanes.verify_ledger(copy),
        real=ctx.lanes.verify_ledger(chain),
    )


def _tampered(entry: LedgerEntry) -> LedgerEntry:
    return entry.model_copy(update={"payload": {**entry.payload, TAMPER_MARK: True}})


def _head(ctx: ServiceContext, workspace_id: str) -> LedgerEntry | None:
    row = ctx.session.scalars(
        select(LedgerEntryRow)
        .where(LedgerEntryRow.workspace_id == workspace_id)
        .order_by(LedgerEntryRow.seq.desc())
        .limit(1)
    ).first()
    return _entry(row) if row else None


def _entry(row: LedgerEntryRow) -> LedgerEntry:
    return LedgerEntry(
        seq=row.seq,
        at=row.at,
        kind=LedgerKind(row.kind),
        subject_id=row.subject_id,
        payload=row.payload,
        prev_hash=row.prev_hash,
        hash=row.hash,
    )
