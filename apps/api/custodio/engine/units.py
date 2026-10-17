"""Common units shared by the engine and the auditor: amounts in base currency and instants in UTC."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal

# Amounts in base currency keep six decimals: exact enough to compare against any limit, and short enough that
# sums are exact, so the engine and the auditor always add up to the very same number.
BASE_QUANTUM = Decimal("0.000001")
NORMALIZED_AMOUNT = re.compile(r"^\d+(?:\.\d+)?$")


def parse_amount(value: str | None) -> Decimal | None:
    """A normalized positive amount such as "12500.00"; anything else counts as not read."""
    if value is None or not NORMALIZED_AMOUNT.match(value.strip()):
        return None
    amount = Decimal(value.strip())
    return amount if amount > 0 else None


def to_base(amount: Decimal | None, currency: str | None, fx: Mapping[str, Decimal]) -> Decimal | None:
    """Units of `currency` -> base currency, or None when the amount, the currency or a valid rate is missing."""
    rate = fx.get(currency) if currency else None
    if amount is None or rate is None or rate <= 0:
        return None
    return (amount / rate).quantize(BASE_QUANTUM, rounding=ROUND_HALF_EVEN)


def as_utc(moment: datetime) -> datetime:
    """Naive datetimes are taken as UTC, so mixed inputs still sort."""
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def same_month(first: date, second: date) -> bool:
    return (first.year, first.month) == (second.year, second.month)
