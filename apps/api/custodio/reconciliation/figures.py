"""Signed amounts as statements write them: `-1.400,00`, `1,400.00-`, `(25.00)`, `USD −12.50`.

The magnitude is read by the invoice reader's own parser (Latin and Anglo formats); the sign is a mark next to that
very number, so the minus inside a reference such as «KT-0921» never turns an amount negative.
"""

from __future__ import annotations

import re
from decimal import Decimal

from custodio.extraction.amounts import parse_amount
from custodio.extraction.errors import AmountFormatError

_NUMBER = re.compile(r"\d(?:[\d.,'  ]*\d)?")
MINUS_SIGNS = "-−–"
_CURRENCY_BEFORE = re.compile(r"(?:[A-Z]{3}|US\$|R\$|\$|€)\s*$")


def signed_amounts_in(text: str) -> list[Decimal]:
    """Every number in `text` that reads as an amount, with the sign written next to it, in order."""
    found: list[Decimal] = []
    for match in _NUMBER.finditer(text):
        try:
            magnitude = parse_amount(match.group())
        except AmountFormatError:
            continue
        found.append(-magnitude if _marked_negative(text, match.start(), match.end()) else magnitude)
    return found


def parse_signed_amount(cell: str) -> Decimal:
    """The one amount of a statement cell, with its sign. Raises AmountFormatError when there is not exactly one."""
    amounts = signed_amounts_in(cell)
    if len(amounts) != 1:
        raise AmountFormatError(f"Se esperaba exactamente un monto en «{cell}» y hay {len(amounts)}.")
    return amounts[0]


def _marked_negative(text: str, start: int, end: int) -> bool:
    before = _CURRENCY_BEFORE.sub("", text[:start].rstrip()).rstrip()
    after = text[end:].lstrip()
    if before.endswith("(") and after.startswith(")"):
        return True
    if before and before[-1] in MINUS_SIGNS:
        preceding = before[:-1]
        return not preceding or not preceding[-1].isalnum()  # «-1.400» and «USD -1.400», never «KT-0921»
    return bool(after) and after[0] in MINUS_SIGNS and not (len(after) > 1 and after[1].isalnum())
