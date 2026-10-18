"""Two independent readings of one invoice, compared by code for R1.

The comparison is recomputed here from each reader's value: the `agree` flags and the status that come with the
reading are never trusted on their own. A field that any reader left unread, a field missing from the comparison or
a reading that did not happen is a disagreement, so the invoice goes to a person.
"""

from __future__ import annotations

from collections.abc import Callable

from custodio.contracts import CrossCheckStatus, FieldCrossCheck, ReadingCrossCheck
from custodio.engine.formatting import join_es, with_cents
from custodio.engine.text import fold, normalize_code, normalize_name
from custodio.engine.units import parse_amount

COMPARED_FIELDS = {
    "supplier_name": "el proveedor",
    "amount": "el monto",
    "currency": "la moneda",
    "account_number": "la cuenta",
}
UNREAD = "(sin leer)"


def disagreements(cross_check: ReadingCrossCheck) -> list[str]:
    """`el monto: 4.800,00 vs 48.000,00` for every compared field the readers do not agree on."""
    by_field: dict[str, FieldCrossCheck] = {comparison.field: comparison for comparison in cross_check.fields}
    found = []
    for name, label in COMPARED_FIELDS.items():
        comparison = by_field.get(name)
        if comparison is None:
            found.append(f"{label}: no se comparó")
        elif not _agree(comparison):
            found.append(f"{label}: {' vs '.join(_shown(name, r.value) for r in comparison.readings)}")
    return found


def problem(cross_check: ReadingCrossCheck) -> str | None:
    """The sentence R1 writes when the two readings do not back each other; None when they do."""
    if cross_check.status is CrossCheckStatus.UNAVAILABLE:
        why = f" ({cross_check.error})" if cross_check.error else ""
        return f"No hubo segunda lectura independiente{why}; sin dos lecturas que coincidan no se paga sola."
    found = disagreements(cross_check)
    if found:
        return f"Las dos lecturas no coinciden en {join_es(found)}."
    if cross_check.status is not CrossCheckStatus.AGREE:
        return "Las dos lecturas no coinciden."
    return None


def agreement(cross_check: ReadingCrossCheck) -> str:
    readers = sorted({reading.reader for c in cross_check.fields for reading in c.readings})
    return f"Las dos lecturas independientes coinciden en proveedor, monto, moneda y cuenta ({join_es(readers)})."


def values_agree(field: str, values: list[str | None]) -> bool:
    """At least two readers, every one of them read the field, and all of them read the same thing once normalized."""
    normalize = _NORMALIZERS[field]
    normalized = [normalize(value) if value and value.strip() else None for value in values]
    return len(normalized) >= 2 and None not in normalized and len(set(normalized)) == 1


def _agree(comparison: FieldCrossCheck) -> bool:
    return values_agree(comparison.field, [reading.value for reading in comparison.readings])


def _amount(value: str) -> str:
    parsed = parse_amount(value)
    return str(parsed.normalize()) if parsed is not None else f"?{value}"


def _shown(name: str, value: str | None) -> str:
    if not value:
        return UNREAD
    parsed = parse_amount(value) if name == "amount" else None
    return with_cents(parsed) if parsed is not None else value


_NORMALIZERS: dict[str, Callable[[str], str]] = {
    "supplier_name": normalize_name,
    "amount": _amount,
    "currency": lambda value: fold(value).strip().upper(),
    "account_number": normalize_code,
}
