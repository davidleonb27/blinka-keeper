"""Dates as invoices write them. Numeric dates are read day first (05/10/2026 is 5 October), as Latin invoices do."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date

from custodio.extraction.text import fold

_MONTH_NAMES = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre",
    "january february march april may june july august september october november december",
    "ene feb mar abr may jun jul ago sep oct nov dic",
    "jan feb mar apr may jun jul aug sep oct nov dec",
)
_MONTHS: dict[str, int] = {
    name: number for names in _MONTH_NAMES for number, name in enumerate(names.split(), start=1)
} | {"sept": 9, "setiembre": 9}
_MONTH = "(" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DAY_FIRST = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
_DAY_MONTH_NAME = re.compile(rf"\b(\d{{1,2}})(?: de |[ -]){_MONTH}(?: de | del |[ -]|, )(\d{{4}})\b")
_MONTH_NAME_DAY = re.compile(rf"\b{_MONTH} (\d{{1,2}}),? (\d{{4}})\b")


def dates_in(text: str) -> set[date]:
    """Every valid calendar date written in `text`."""
    folded = fold(text)
    return set(_valid(_candidates(folded)))


def _candidates(folded: str) -> Iterator[tuple[int, int, int]]:
    for year, month, day in _ISO.findall(folded):
        yield int(year), int(month), int(day)
    for day, month, year in _DAY_FIRST.findall(folded):
        yield int(year), int(month), int(day)
    for day, month_name, year in _DAY_MONTH_NAME.findall(folded):
        yield int(year), _MONTHS[month_name], int(day)
    for month_name, day, year in _MONTH_NAME_DAY.findall(folded):
        yield int(year), _MONTHS[month_name], int(day)


def _valid(candidates: Iterator[tuple[int, int, int]]) -> Iterator[date]:
    for year, month, day in candidates:
        try:
            yield date(year, month, day)
        except ValueError:
            continue
