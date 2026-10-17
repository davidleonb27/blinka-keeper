"""Append-only ledger chained with SHA-256.

hash = sha256(prev_hash + canonical_json({seq, at, kind, subject_id, payload})); the first entry links to
GENESIS_HASH. Payloads are stored in their canonical JSON form, so reading an entry back from a database yields
the very values that were hashed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from custodio.contracts import LedgerEntry, LedgerKind, LedgerVerification
from custodio.engine.errors import CanonicalJsonError

GENESIS_HASH = "0" * 64
FIRST_SEQ = 1


def canonical_json(obj: object) -> str:
    """Sorted keys, no spaces, Decimal as a normalized string, dates and datetimes as ISO-8601 (UTC)."""
    try:
        return json.dumps(_plain(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as error:
        raise CanonicalJsonError(str(error)) from error


def next_entry(
    prev: LedgerEntry | None,
    *,
    kind: LedgerKind,
    subject_id: str | None,
    payload: Mapping[str, Any],
    at: datetime,
) -> LedgerEntry:
    seq = prev.seq + 1 if prev else FIRST_SEQ
    prev_hash = prev.hash if prev else GENESIS_HASH
    stored_payload = json.loads(canonical_json(payload))
    entry_hash = _entry_hash(prev_hash, seq=seq, at=at, kind=kind, subject_id=subject_id, payload=stored_payload)
    return LedgerEntry(
        seq=seq,
        at=at,
        kind=kind,
        subject_id=subject_id,
        payload=stored_payload,
        prev_hash=prev_hash,
        hash=entry_hash,
    )


def verify(entries: Sequence[LedgerEntry]) -> LedgerVerification:
    """Walk the chain from the start; report the seq where it first breaks and the last trustworthy hash."""
    head_hash: str | None = None
    for position, entry in enumerate(entries):
        expected_seq = FIRST_SEQ + position
        if not _is_intact(entry, expected_seq=expected_seq, prev_hash=head_hash or GENESIS_HASH):
            return LedgerVerification(
                valid=False, length=len(entries), first_broken_seq=expected_seq, head_hash=head_hash
            )
        head_hash = entry.hash
    return LedgerVerification(valid=True, length=len(entries), first_broken_seq=None, head_hash=head_hash)


def _is_intact(entry: LedgerEntry, *, expected_seq: int, prev_hash: str) -> bool:
    recomputed = _entry_hash(
        entry.prev_hash,
        seq=entry.seq,
        at=entry.at,
        kind=entry.kind,
        subject_id=entry.subject_id,
        payload=entry.payload,
    )
    return entry.seq == expected_seq and entry.prev_hash == prev_hash and entry.hash == recomputed


def _entry_hash(
    prev_hash: str,
    *,
    seq: int,
    at: datetime,
    kind: LedgerKind,
    subject_id: str | None,
    payload: Mapping[str, Any],
) -> str:
    body = canonical_json({"seq": seq, "at": at, "kind": kind, "subject_id": subject_id, "payload": payload})
    return hashlib.sha256((prev_hash + body).encode()).hexdigest()


def _plain(value: object) -> object:
    """Turn a value into plain JSON types, rejecting anything without one deterministic spelling."""
    if isinstance(value, Enum):
        return _plain(value.value)
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _utc_text(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {_key(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    raise CanonicalJsonError(f"cannot write {type(value).__name__} as canonical JSON")


def _key(key: object) -> str:
    if not isinstance(key, str):
        raise CanonicalJsonError(f"object keys must be strings, got {type(key).__name__}")
    return key


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise CanonicalJsonError(f"cannot write non-finite decimal {value}")
    return "0" if value.is_zero() else format(value.normalize(), "f")


def _utc_text(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")
