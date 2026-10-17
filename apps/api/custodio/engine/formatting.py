"""Spanish (es-CO) spelling of the numbers that go into reasons and explanations: `USD 12.500`, `COP 4.200.000`."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")
HUNDRED = Decimal(100)
MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
QUOTE_LIMIT = 90


def money(amount: Decimal, currency: str) -> str:
    """Rounded to cents; the cents are shown only when they are not zero."""
    cents = amount.quantize(CENT, rounding=ROUND_HALF_EVEN)
    places = 0 if cents == cents.to_integral_value() else 2
    return f"{currency} {_es_number(cents, places)}"


def percent(ratio: Decimal) -> str:
    return f"{_compact(ratio * HUNDRED)} %"


def signed_percent(value: Decimal) -> str:
    """A percentage already expressed in points, with its sign: `+23,28 %`, `−2 %`."""
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return f"{sign}{_compact(abs(value))} %"


def day_month(day: date) -> str:
    return f"{day.day} de {MONTHS[day.month - 1]}"


def clip(text: str) -> str:
    """One line, at most QUOTE_LIMIT characters, for quoting a document inside a reason."""
    flat = " ".join(text.split())
    return flat if len(flat) <= QUOTE_LIMIT else flat[: QUOTE_LIMIT - 1] + "…"


def _compact(value: Decimal) -> str:
    """At most two decimals, without trailing zeros: `97,5`, `2,01`, `90`."""
    hundredths = value.quantize(CENT, rounding=ROUND_HALF_EVEN)
    places = next(places for places in (0, 1, 2) if hundredths == round(hundredths, places))
    return _es_number(hundredths, places)


def _es_number(value: Decimal, places: int) -> str:
    english = f"{value:,.{places}f}"
    return english.replace(",", "\0").replace(".", ",").replace("\0", ".")
