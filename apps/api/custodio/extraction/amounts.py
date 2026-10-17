"""Amounts and currencies as invoices write them.

Latin invoices group thousands with dots and mark decimals with a comma (`4.200.000,00`); Anglo invoices do the
opposite (`4,200,000.00`). When a number has a single mark followed by exactly three digits (`1.000`, `1,234`) the
mark groups thousands: invoices almost never carry three decimals. A bare `$` names no currency: it is the peso sign
in most of Latin America and the dollar sign elsewhere.
"""

from __future__ import annotations

import re
from decimal import Decimal

from custodio.extraction.errors import AmountFormatError
from custodio.extraction.text import fold

_NUMBER = re.compile(r"\d(?:[\d.,'  ]*\d)?")
_GROUPING_ONLY = str.maketrans("", "", "'  ")
_MARKS = ".,"
_GROUP_SIZE = 3

_CURRENCY_MARKERS: dict[str, tuple[str, ...]] = {
    "USD": (r"\busd\b", r"\bus\$", r"\bu\$s\b", r"\bdolares\b", r"\bdollars\b"),
    "COP": (r"\bcop\b", r"\bcol\$", r"\bpesos colombianos\b"),
    "MXN": (r"\bmxn\b", r"\bmx\$", r"\bpesos mexicanos\b"),
    "BRL": (r"\bbrl\b", r"\br\$", r"\breais\b", r"\breales\b"),
    "CLP": (r"\bclp\b", r"\bpesos chilenos\b"),
    "EUR": (r"\beur\b", r"€", r"\beuros?\b"),
}
_CURRENCY_PATTERNS = {code: re.compile("|".join(markers)) for code, markers in _CURRENCY_MARKERS.items()}
_BARE_DOLLAR = re.compile(r"(?<![A-Za-z])\$")

_LATIN_STYLE = frozenset({"COP", "CLP", "BRL", "EUR"})
_WITHOUT_CENTS = frozenset({"CLP"})


def parse_amount(text: str) -> Decimal:
    """Read the one amount in `text` (symbols and labels around it are ignored)."""
    numbers = _NUMBER.findall(text)
    if len(numbers) != 1:
        raise AmountFormatError(f"Se esperaba exactamente un monto en «{text}» y hay {len(numbers)}.")
    return _parse_number(numbers[0])


def amounts_in(text: str) -> list[Decimal]:
    """Every number in `text` that reads unambiguously as an amount, in order."""
    found: list[Decimal] = []
    for number in _NUMBER.findall(text):
        try:
            found.append(_parse_number(number))
        except AmountFormatError:
            continue
    return found


def currencies_named(text: str) -> set[str]:
    """ISO codes that `text` names explicitly (code, prefixed sign or currency name)."""
    folded = fold(text)
    return {code for code, pattern in _CURRENCY_PATTERNS.items() if pattern.search(folded)}


def has_bare_dollar(text: str) -> bool:
    return _BARE_DOLLAR.search(text) is not None


def format_amount(amount: Decimal, currency: str) -> str:
    """Write `amount` the way invoices in `currency` usually do, prefixed by the ISO code."""
    decimals = 0 if currency in _WITHOUT_CENTS else 2
    anglo = f"{amount:,.{decimals}f}"
    written = anglo.translate(str.maketrans(",.", ".,")) if currency in _LATIN_STYLE else anglo
    return f"{currency} {written}"


def _parse_number(number: str) -> Decimal:
    compact = number.translate(_GROUPING_ONLY)
    marks = [char for char in compact if char in _MARKS]
    if not marks:
        return Decimal(compact)
    last = marks[-1]
    if len(set(marks)) == len(_MARKS):
        if marks.count(last) != 1:
            raise AmountFormatError(f"«{number}» usa la marca decimal más de una vez.")
        grouping = next(mark for mark in _MARKS if mark != last)
        return _join(compact, grouping=grouping, decimal=last)
    if len(marks) > 1 or _groups_thousands(compact, last):
        return _join(compact, grouping=last, decimal=None)
    return _join(compact, grouping=None, decimal=last)


def _groups_thousands(compact: str, mark: str) -> bool:
    integer, fraction = compact.split(mark)
    return len(fraction) == _GROUP_SIZE and integer != "0"


def _join(compact: str, *, grouping: str | None, decimal: str | None) -> Decimal:
    integer, _, fraction = compact.partition(decimal) if decimal else (compact, "", "")
    groups = integer.split(grouping) if grouping else [integer]
    if not _valid_groups(groups):
        raise AmountFormatError(f"«{compact}» no agrupa los miles de a tres dígitos.")
    return Decimal("".join(groups) + (f".{fraction}" if fraction else ""))


def _valid_groups(groups: list[str]) -> bool:
    first, rest = groups[0], groups[1:]
    if not first.isdigit() or not all(group.isdigit() for group in rest):
        return False
    return (not rest or 1 <= len(first) <= _GROUP_SIZE) and all(len(group) == _GROUP_SIZE for group in rest)
