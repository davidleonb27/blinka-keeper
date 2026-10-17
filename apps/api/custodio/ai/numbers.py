"""Reading numbers the way people write them in Spanish: "3.000", "4.200.000,50", "80 mil", "tres mil".

Used as evidence checks: the compiler accepts an amount only if the user's quote states it, and the narrator
accepts a text only if each of its numbers exists in the decision.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

_TOKEN = re.compile(r"\d[\d.,]*\d|\d|[a-z]+")
_THOUSANDS_GROUP = 3

# fmt: off
_UNITS: dict[str, int] = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiun": 21, "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28,
    "veintinueve": 29, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
    "ochenta": 80, "noventa": 90, "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300, "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500, "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700, "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}
# fmt: on
_THOUSAND_WORDS = {"mil", "k", "luca", "lucas"}  # "50 lucas" is 50 mil in Colombia and Chile
_MILLION_WORDS = {"millon", "millones", "mm", "palo", "palos"}
_CONNECTOR = "y"
_THOUSAND = "mil"


def parse_amount(token: str) -> Decimal | None:
    """Parse one written number. A lone separator followed by exactly three digits is a thousands separator."""
    if not re.fullmatch(r"\d[\d.,]*", token) or not token[-1].isdigit():
        return None
    has_dot, has_comma = "." in token, "," in token
    if has_dot and has_comma:
        decimal_sep = "." if token.rfind(".") > token.rfind(",") else ","
        return _with_separators(token, thousands="," if decimal_sep == "." else ".", decimal=decimal_sep)
    if not (has_dot or has_comma):
        return Decimal(token)
    separator = "." if has_dot else ","
    if token.count(separator) > 1 or _looks_like_thousands(token, separator):
        return _with_separators(token, thousands=separator, decimal=None)
    return _decimal(token.replace(separator, "."))


def amounts_in(text: str) -> set[Decimal]:
    """Every number a reader would see in `text`, with "mil"/"millones" applied and number words read."""
    tokens = _TOKEN.findall(_strip_accents(text))
    found: set[Decimal] = set()
    index = 0
    while index < len(tokens):
        value, index = _read_number(tokens, index)
        if value is not None:
            found.add(value.normalize())
    return found


def fold(text: str) -> str:
    """Lowercase without accents and with single spaces, for comparing what people wrote."""
    return " ".join(_strip_accents(text).split())


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def _looks_like_thousands(token: str, separator: str) -> bool:
    head, tail = token.split(separator)
    return len(tail) == _THOUSANDS_GROUP and len(head) <= _THOUSANDS_GROUP


def _with_separators(token: str, *, thousands: str, decimal: str | None) -> Decimal | None:
    integer, _, fraction = token.partition(decimal) if decimal else (token, "", "")
    if decimal and (not fraction or decimal in fraction or thousands in fraction):
        return None
    groups = integer.split(thousands)
    if not 1 <= len(groups[0]) <= _THOUSANDS_GROUP or any(len(g) != _THOUSANDS_GROUP for g in groups[1:]):
        return None
    return _decimal("".join(groups) + (f".{fraction}" if fraction else ""))


def _decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _read_number(tokens: list[str], index: int) -> tuple[Decimal | None, int]:
    """Read the number starting at tokens[index], if any; return it and the index after it."""
    token = tokens[index]
    if token[0].isdigit():
        value = parse_amount(token)
        index += 1
        if value is not None and index < len(tokens):
            multiplier = _multiplier(tokens[index])
            if multiplier is not None:
                return value * multiplier, index + 1
        return value, index
    if token in _UNITS or token in _MILLION_WORDS | {_THOUSAND}:
        return _read_words(tokens, index)
    return None, index + 1


def _multiplier(token: str) -> Decimal | None:
    if token in _THOUSAND_WORDS:
        return Decimal(1000)
    if token in _MILLION_WORDS:
        return Decimal(1_000_000)
    return None


def _read_words(tokens: list[str], index: int) -> tuple[Decimal | None, int]:
    """Spanish number words: "dos mil quinientos", "un millón doscientos mil", "cuarenta y cinco"."""
    total, current, seen = 0, 0, False
    while index < len(tokens):
        token = tokens[index]
        if token in _UNITS:
            current += _UNITS[token]
        elif token == _THOUSAND:
            total += max(current, 1) * 1000
            current = 0
        elif token in _MILLION_WORDS:
            total = (total + max(current, 1)) * 1_000_000
            current = 0
        elif token == _CONNECTOR and seen and index + 1 < len(tokens) and tokens[index + 1] in _UNITS:
            pass
        else:
            break
        seen = True
        index += 1
    return (Decimal(total + current) if seen else None), index
