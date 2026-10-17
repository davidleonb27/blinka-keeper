"""Code checks every value the model read: the quote must exist in the source and must back the value.

Only this module sets `ExtractedField.verified`. A quote is searched exactly as written, except that any run of
whitespace matches any other (line breaks and column gaps differ between extractors). Whether the quote backs the
value depends on the kind of field: amounts must parse to the same number, dates to the same day, identifiers and
accounts must carry the same characters, currencies need an explicit marker.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from enum import StrEnum

from custodio.contracts import Evidence, ExtractedField
from custodio.extraction.amounts import amounts_in, currencies_named, has_bare_dollar
from custodio.extraction.dates import dates_in
from custodio.extraction.source import SourceText
from custodio.extraction.text import fold

# A currency read from a bare "$" is a guess between pesos and dollars; R1 must send it to a person.
AMBIGUOUS_CURRENCY_CONFIDENCE = 0.3

_PLAIN_DECIMAL = re.compile(r"\d+(?:\.\d+)?")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ISO_CURRENCY = re.compile(r"[A-Z]{3}")
_CENTS = 2


class FieldKind(StrEnum):
    TEXT = "text"  # names, banks, descriptions
    IDENTIFIER = "identifier"  # invoice numbers
    DIGITS = "digits"  # tax ids and bank accounts
    AMOUNT = "amount"
    DATE = "date"
    CURRENCY = "currency"


def verified_field(
    kind: FieldKind, *, value: str | None, quote: str | None, confidence: float, source: SourceText
) -> ExtractedField:
    """Turn what the model read into an ExtractedField whose `verified` flag code has earned."""
    normalized = normalize_value(kind, value)
    span = locate(quote, source.text) if quote else None
    verified = bool(quote and span and normalized and supports(kind, normalized, quote))
    if kind is FieldKind.CURRENCY and not verified and has_bare_dollar(quote or ""):
        confidence = min(confidence, AMBIGUOUS_CURRENCY_CONFIDENCE)
    return ExtractedField(
        value=normalized, evidence=_evidence(quote, span, source), confidence=confidence, verified=verified
    )


def locate(quote: str, source: str) -> tuple[int, int] | None:
    """Span of `quote` in `source`, matching any whitespace run with any other; None when absent."""
    words = quote.split()
    if not words:
        return None
    match = re.search(r"\s+".join(map(re.escape, words)), source)
    return match.span() if match else None


def normalize_value(kind: FieldKind, value: str | None) -> str | None:
    """The canonical form of `value` for its kind, or None when it is missing or not in that form."""
    cleaned = value.strip() if value else ""
    return _NORMALIZERS[kind](cleaned) if cleaned else None


def supports(kind: FieldKind, value: str, quote: str) -> bool:
    """Whether `quote` backs `value`, which must already be in the canonical form of `kind`."""
    return _SUPPORTS[kind](value, quote)


def _evidence(quote: str | None, span: tuple[int, int] | None, source: SourceText) -> Evidence | None:
    if quote is None:
        return None
    if span is None:
        return Evidence(quote=quote)
    start, end = span
    return Evidence(quote=quote, page=source.page_at(start), char_start=start, char_end=end)


def _normalize_amount(value: str) -> str | None:
    if not _PLAIN_DECIMAL.fullmatch(value):
        return None
    decimals = len(value.partition(".")[2])
    return f"{Decimal(value):.{max(decimals, _CENTS)}f}"


def _normalize_date(value: str) -> str | None:
    if not _ISO_DATE.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _normalize_currency(value: str) -> str | None:
    code = value.upper()
    return code if _ISO_CURRENCY.fullmatch(code) else None


def _same_text(value: str, quote: str) -> bool:
    return fold(value) in fold(quote)


def _same_characters(value: str, quote: str) -> bool:
    characters = [char for char in value if char.isalnum()]
    if not characters:
        return False
    separators = r"[\s\-./#_]*"
    pattern = r"(?<![0-9A-Za-z])" + separators.join(map(re.escape, characters)) + r"(?![0-9A-Za-z])"
    return re.search(pattern, quote, flags=re.IGNORECASE) is not None


def _same_digits(value: str, quote: str) -> bool:
    digits = [char for char in value if char.isdigit()]
    if not digits:
        return False
    pattern = r"(?<!\d)" + r"[\s.\-]*".join(digits) + r"(?!\d)"
    return re.search(pattern, quote) is not None


def _same_amount(value: str, quote: str) -> bool:
    return Decimal(value) in amounts_in(quote)


def _same_date(value: str, quote: str) -> bool:
    return date.fromisoformat(value) in dates_in(quote)


def _names_currency(value: str, quote: str) -> bool:
    return value in currencies_named(quote)


def _trimmed(value: str) -> str:
    return value


_NORMALIZERS: dict[FieldKind, Callable[[str], str | None]] = {
    FieldKind.TEXT: _trimmed,
    FieldKind.IDENTIFIER: _trimmed,
    FieldKind.DIGITS: _trimmed,
    FieldKind.AMOUNT: _normalize_amount,
    FieldKind.DATE: _normalize_date,
    FieldKind.CURRENCY: _normalize_currency,
}
_SUPPORTS: dict[FieldKind, Callable[[str, str], bool]] = {
    FieldKind.TEXT: _same_text,
    FieldKind.IDENTIFIER: _same_characters,
    FieldKind.DIGITS: _same_digits,
    FieldKind.AMOUNT: _same_amount,
    FieldKind.DATE: _same_date,
    FieldKind.CURRENCY: _names_currency,
}
