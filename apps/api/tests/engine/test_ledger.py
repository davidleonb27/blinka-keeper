import hashlib
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custodio.contracts import LedgerEntry, LedgerKind
from custodio.engine.errors import CanonicalJsonError
from custodio.engine.ledger import GENESIS_HASH, canonical_json, next_entry, verify

AT = datetime(2026, 10, 16, 9, 30, tzinfo=UTC)


def chain(payloads: list[dict[str, Any]]) -> list[LedgerEntry]:
    entries: list[LedgerEntry] = []
    for index, payload in enumerate(payloads):
        prev = entries[-1] if entries else None
        entries.append(
            next_entry(
                prev,
                kind=LedgerKind.DECISION,
                subject_id=f"F-{index:03d}",
                payload=payload,
                at=AT + timedelta(minutes=index),
            )
        )
    return entries


def test_canonical_json_sorts_keys_and_drops_spaces() -> None:
    assert canonical_json({"b": 1, "a": [True, None, "x"]}) == '{"a":[true,null,"x"],"b":1}'


def test_canonical_json_writes_decimals_as_normalized_strings() -> None:
    assert canonical_json({"x": Decimal("12500.00")}) == '{"x":"12500"}'
    assert canonical_json({"x": Decimal("1E+3")}) == '{"x":"1000"}'
    assert canonical_json({"x": Decimal("0.50")}) == '{"x":"0.5"}'
    assert canonical_json({"x": Decimal("-0.00")}) == '{"x":"0"}'


def test_canonical_json_writes_datetimes_in_utc() -> None:
    bogota = timezone(timedelta(hours=-5))
    assert canonical_json(datetime(2026, 10, 16, 4, 30, tzinfo=bogota)) == '"2026-10-16T09:30:00Z"'
    assert canonical_json(datetime(2026, 10, 16, 9, 30)) == '"2026-10-16T09:30:00Z"'
    assert canonical_json(date(2026, 10, 16)) == '"2026-10-16"'


def test_canonical_json_keeps_non_ascii_text() -> None:
    assert canonical_json("Cupo de pago automático") == '"Cupo de pago automático"'


def test_canonical_json_rejects_what_it_cannot_write_deterministically() -> None:
    with pytest.raises(CanonicalJsonError):
        canonical_json({"x": {1, 2}})
    with pytest.raises(CanonicalJsonError):
        canonical_json({1: "non-string key"})
    with pytest.raises(CanonicalJsonError):
        canonical_json(float("nan"))


def test_first_entry_links_to_the_genesis_hash() -> None:
    [entry] = chain([{"verdict": "pay"}])
    assert entry.seq == 1
    assert entry.prev_hash == GENESIS_HASH == "0" * 64
    body = canonical_json(
        {"seq": 1, "at": AT, "kind": "decision", "subject_id": "F-000", "payload": {"verdict": "pay"}}
    )
    assert entry.hash == hashlib.sha256((GENESIS_HASH + body).encode()).hexdigest()


def test_entries_link_to_the_previous_hash() -> None:
    first, second = chain([{"n": 1}, {"n": 2}])
    assert second.seq == 2
    assert second.prev_hash == first.hash


def test_payload_is_stored_in_its_json_form_so_a_database_round_trip_keeps_the_hash() -> None:
    [entry] = chain([{"amount": Decimal("4800.00"), "on": date(2026, 10, 1)}])
    assert entry.payload == {"amount": "4800", "on": "2026-10-01"}
    restored = LedgerEntry.model_validate_json(entry.model_dump_json())
    assert verify([restored]).valid


def test_an_empty_ledger_is_valid() -> None:
    assert verify([]).model_dump() == {"valid": True, "length": 0, "first_broken_seq": None, "head_hash": None}


def test_an_untouched_chain_is_valid() -> None:
    entries = chain([{"n": n} for n in range(5)])
    result = verify(entries)
    assert result.valid
    assert result.length == 5
    assert result.first_broken_seq is None
    assert result.head_hash == entries[-1].hash


TAMPERS: dict[str, Any] = {
    "seq": 99,
    "at": AT + timedelta(days=1),
    "kind": LedgerKind.PAYMENT,
    "subject_id": "F-999",
    "payload": {"n": "tampered"},
    "prev_hash": "f" * 64,
    "hash": "e" * 64,
}


@pytest.mark.parametrize("field", sorted(TAMPERS))
@given(target=st.integers(min_value=0, max_value=5))
def test_tampering_any_field_of_any_entry_is_detected_at_that_seq(field: str, target: int) -> None:
    entries = chain([{"n": n} for n in range(6)])
    entries[target] = entries[target].model_copy(update={field: TAMPERS[field]})
    result = verify(entries)
    assert not result.valid
    assert result.first_broken_seq == target + 1
    assert result.head_hash == (entries[target - 1].hash if target else None)


def test_removing_an_entry_breaks_the_chain_where_it_was() -> None:
    entries = chain([{"n": n} for n in range(4)])
    del entries[1]
    assert verify(entries).first_broken_seq == 2
