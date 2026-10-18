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
QUOTE_LIMIT = 120


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
    return f"{day.day} de {month_name(day)}"


def long_date(day: date) -> str:
    return f"{day_month(day)} de {day.year}"


def two_decimals(value: float) -> str:
    """`0,92`."""
    return _es_number(Decimal(str(value)), 2)


def with_cents(amount: Decimal) -> str:
    """`4.800,00`: an amount as read, cents always shown."""
    return _es_number(amount, 2)


def thousands(count: int) -> str:
    """`19.457`."""
    return _es_number(Decimal(count), 0)


def clip(text: str) -> str:
    """One line, at most QUOTE_LIMIT characters, for quoting a document inside a reason."""
    flat = " ".join(text.split())
    return flat if len(flat) <= QUOTE_LIMIT else flat[: QUOTE_LIMIT - 1] + "…"


def plus_minus_percent(points: Decimal) -> str:
    return f"±{_compact(points)} %"


def month_name(day: date) -> str:
    return MONTHS[day.month - 1]


def counted(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def join_es(parts: list[str]) -> str:
    """`a`, `a y b`, `a, b y c`."""
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " y " + parts[-1]


def money_with_base(amount: Decimal | None, currency: str | None, amount_base: Decimal, base: str) -> str:
    """`USD 4.800`, or `COP 26.650.000 (≈ USD 6.500)` when the invoice is in another currency."""
    if currency == base or amount is None or currency is None:
        return money(amount_base, base)
    return f"{money(amount, currency)} (≈ {money(amount_base, base)})"


def _compact(value: Decimal) -> str:
    """At most two decimals, without trailing zeros: `97,5`, `2,01`, `90`."""
    hundredths = value.quantize(CENT, rounding=ROUND_HALF_EVEN)
    places = next(places for places in (0, 1, 2) if hundredths == round(hundredths, places))
    return _es_number(hundredths, places)


def _es_number(value: Decimal, places: int) -> str:
    english = f"{value:,.{places}f}"
    return english.replace(",", "\0").replace(".", ",").replace("\0", ".")
