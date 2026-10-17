"""Reading without a model: `Campo: valor` lines, read by code.

A deployment without ANTHROPIC_API_KEY still reads plain text and PDFs with text this way. Each field takes the first
line of the document that states it with a known label, so the header of a payment intent always wins over a document
attached below it. The value goes through the same verification as a model's reading; a field no label states stays
unread, and R1 sends the invoice to a person instead of anyone guessing it.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from custodio.contracts import ExtractedField
from custodio.extraction.amounts import currencies_named, parse_amount
from custodio.extraction.dates import dates_in
from custodio.extraction.errors import AmountFormatError
from custodio.extraction.source import SourceText
from custodio.extraction.structure import FIELD_KINDS, FieldReading
from custodio.extraction.verify import FieldKind, verified_field

READER = "etiquetas"
# A labelled value is read by code, not guessed; verification still decides what counts as read.
LABELLED_CONFIDENCE = 0.95
UNREAD_CONFIDENCE = 0.0

_NUMBER_MARK = r"[ \t]+(?:no\.?|n[°º.]+|#)"


def _colon(pattern: str) -> str:
    return pattern + r"[ \t]*:[ \t]*"


def _optional_colon(pattern: str) -> str:
    return pattern + r"(?!\w)[ \t]*:?[ \t]*"


_LABELS: dict[str, tuple[str, ...]] = {
    "supplier_name": tuple(map(_colon, (r"proveedor", r"emisor", r"raz[oó]n social", r"titular"))),
    "supplier_tax_id": (
        _colon(r"identificaci[oó]n tributaria"),
        *map(_optional_colon, (r"nit", r"rfc", r"cnpj", r"rut", r"ruc", r"cuit", r"tax id")),
    ),
    "invoice_number": (
        _colon(r"n[uú]mero de factura"),
        _optional_colon(r"factura(?:[ \t]+electr[oó]nica(?:[ \t]+de[ \t]+venta)?)?" + _NUMBER_MARK),
    ),
    "issue_date": tuple(map(_colon, (r"fecha de emisi[oó]n", r"fecha de expedici[oó]n"))),
    "due_date": tuple(map(_colon, (r"fecha de vencimiento", r"vence"))),
    "amount": tuple(map(_colon, (r"total a pagar", r"valor a pagar", r"monto", r"total"))),
    "currency": (_colon(r"moneda"),),
    "bank_name": (_colon(r"banco"),),
    "account_number": (
        _optional_colon(r"(?:n[uú]mero de )?cuenta(?:[ \t]+de[ \t]+ahorros|[ \t]+corriente)?" + _NUMBER_MARK),
        _colon(r"(?:n[uú]mero de )?cuenta(?:[ \t]+de[ \t]+ahorros|[ \t]+corriente)?"),
    ),
    "description": tuple(map(_colon, (r"concepto", r"descripci[oó]n"))),
}
_LINES = {
    name: re.compile(rf"^[ \t]*(?:{'|'.join(labels)})(?P<value>\S[^\n]*?)[ \t]*$", re.IGNORECASE | re.MULTILINE)
    for name, labels in _LABELS.items()
}
_CODE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9\-./]*[A-Za-z0-9])?")
_DIGIT_GROUPS = re.compile(r"\d(?:[\d.\-]|[ ](?=\d))*")


def read_fields(source: SourceText) -> FieldReading:
    """Every field a label states, quoted with its whole line and verified; the rest unread."""
    text = source.text
    stated = {name: pattern.search(text) for name, pattern in _LINES.items()}
    values = {name: _value(name, match.group("value")) if match else None for name, match in stated.items()}
    values["currency"] = values["currency"] or _currency_of(stated["amount"])
    quotes = {name: match.group(0).strip() if match else None for name, match in stated.items()}
    if stated["currency"] is None:
        quotes["currency"] = quotes["amount"]
    fields = {name: _field(kind, values[name], quotes[name], source) for name, kind in FIELD_KINDS.items()}
    return FieldReading(fields=fields, model=READER)


def _field(kind: FieldKind, value: str | None, quote: str | None, source: SourceText) -> ExtractedField:
    if value is None:
        return verified_field(kind, value=None, quote=None, confidence=UNREAD_CONFIDENCE, source=source)
    return verified_field(kind, value=value, quote=quote, confidence=LABELLED_CONFIDENCE, source=source)


def _value(name: str, stated: str) -> str | None:
    return _READERS[FIELD_KINDS[name]](stated)


def _currency_of(amount_line: re.Match[str] | None) -> str | None:
    return _only(currencies_named(amount_line.group("value"))) if amount_line else None


def _amount(stated: str) -> str | None:
    try:
        return f"{parse_amount(stated):f}"
    except AmountFormatError:
        return None


def _date(stated: str) -> str | None:
    day = _only(dates_in(stated))
    return day.isoformat() if day else None


def _currency(stated: str) -> str | None:
    return _only(currencies_named(stated))


def _first(pattern: re.Pattern[str]) -> Callable[[str], str | None]:
    def first(stated: str) -> str | None:
        match = pattern.search(stated)
        return match.group(0) if match else None

    return first


def _as_written(stated: str) -> str | None:
    return stated


def _only[T](found: set[T]) -> T | None:
    return next(iter(found)) if len(found) == 1 else None


_READERS: dict[FieldKind, Callable[[str], str | None]] = {
    FieldKind.TEXT: _as_written,
    FieldKind.IDENTIFIER: _first(_CODE),
    FieldKind.DIGITS: _first(_DIGIT_GROUPS),
    FieldKind.AMOUNT: _amount,
    FieldKind.DATE: _date,
    FieldKind.CURRENCY: _currency,
}
