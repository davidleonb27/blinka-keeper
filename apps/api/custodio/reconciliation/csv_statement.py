"""Bank statements exported as CSV, read by code alone.

Separator (`;`, `,` or tab), header row and columns (date, description, amount or debit/credit, currency, reference)
are detected from the usual Spanish and English export headers. A row whose date or amount cannot be read stays
NO LEÍDO with its text; nothing is filled in. Numeric dates are day first unless the file itself proves otherwise
(a second part above 12), or its headers are English and nothing in it decides.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from custodio.extraction.dates import dates_in
from custodio.extraction.errors import AmountFormatError
from custodio.extraction.text import fold
from custodio.reconciliation.errors import StatementFormatError
from custodio.reconciliation.figures import parse_signed_amount
from custodio.reconciliation.models import Statement, StatementMovement

READER = "csv"
SEPARATORS = (";", ",", "\t")
HEADER_SEARCH_ROWS = 15
MAX_MOVEMENTS = 2000
MONTHS_IN_YEAR = 12
CENTURY = 2000
_BALANCE_ROW = re.compile(r"^(saldo|total|balance|opening balance|closing balance)\b")
_ISO_DATE = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_NUMERIC_DATE = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})$")
_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")
_CURRENCY_SYMBOLS = re.compile(r"US\$|R\$")
_WORD = re.compile(r"[^\W\d_]+")


class Role(StrEnum):
    DATE = "date"
    DESCRIPTION = "description"
    AMOUNT = "amount"
    DEBIT = "debit"
    CREDIT = "credit"
    CURRENCY = "currency"
    REFERENCE = "reference"


SPANISH_HEADERS: dict[Role, tuple[str, ...]] = {
    Role.DATE: ("fecha", "fecha operacion", "fecha de operacion", "fecha valor", "fecha movimiento", "fecha contable"),
    Role.DESCRIPTION: ("descripcion", "concepto", "detalle", "detalles", "glosa", "movimiento", "beneficiario"),
    Role.AMOUNT: ("monto", "importe", "valor", "cantidad"),
    Role.DEBIT: ("debito", "debitos", "cargo", "cargos", "retiro", "retiros", "egreso", "egresos", "debe"),
    Role.CREDIT: ("credito", "creditos", "abono", "abonos", "deposito", "depositos", "ingreso", "ingresos", "haber"),
    Role.CURRENCY: ("moneda", "divisa"),
    Role.REFERENCE: ("referencia", "ref", "numero de referencia", "documento", "comprobante", "id transaccion"),
}
ENGLISH_HEADERS: dict[Role, tuple[str, ...]] = {
    Role.DATE: ("date", "transaction date", "posting date", "value date", "booking date"),
    Role.DESCRIPTION: ("description", "details", "transaction details", "narrative", "memo", "payee"),
    Role.AMOUNT: ("amount", "value", "transaction amount"),
    Role.DEBIT: ("debit", "debits", "withdrawal", "withdrawals", "money out", "paid out"),
    Role.CREDIT: ("credit", "credits", "deposit", "deposits", "money in", "paid in"),
    Role.CURRENCY: ("currency", "ccy"),
    Role.REFERENCE: ("reference", "ref no", "transaction id"),
}
REQUIRED = (Role.DATE, Role.DESCRIPTION)
AMOUNT_ROLES = (Role.AMOUNT, Role.DEBIT, Role.CREDIT)


class DateOrder(StrEnum):
    DAY_FIRST = "día/mes"
    MONTH_FIRST = "mes/día"


@dataclass(frozen=True)
class Header:
    line: int  # 0-based index of the header line
    separator: str
    columns: dict[Role, int]
    english: bool


def read_csv_statement(data: bytes, *, default_currency: str) -> Statement:
    lines = _decode(data).splitlines()
    header = _find_header(lines)
    rows = [(number, line, _cells(line, header.separator)) for number, line in _data_lines(lines, header)]
    if len(rows) > MAX_MOVEMENTS:
        raise StatementFormatError(f"El extracto trae más de {MAX_MOVEMENTS} movimientos; divídelo por mes.")
    if not rows:
        raise StatementFormatError("El extracto no trae movimientos.")
    order, warnings = _date_order([_cell(cells, header, Role.DATE) for _, _, cells in rows], english=header.english)
    movements = [
        _movement(position, number, line, cells, header, order, default_currency)
        for position, (number, line, cells) in enumerate(rows, start=1)
    ]
    return Statement(movements=movements, reader=READER, currency=default_currency, warnings=warnings)


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _cells(line: str, separator: str) -> list[str]:
    return [cell.strip() for cell in next(csv.reader([line], delimiter=separator), [])]


def _find_header(lines: Sequence[str]) -> Header:
    candidates = [
        header
        for separator in SEPARATORS
        for index, line in enumerate(lines[:HEADER_SEARCH_ROWS])
        if (header := _header(index, line, separator)) is not None
    ]
    if not candidates:
        raise StatementFormatError(
            "No encontramos las columnas de fecha, descripción y monto (o cargo y abono) en las primeras "
            f"{HEADER_SEARCH_ROWS} filas del archivo."
        )
    return min(candidates, key=lambda header: (header.line, -len(header.columns)))


def _header(index: int, line: str, separator: str) -> Header | None:
    names = [_header_name(cell) for cell in _cells(line, separator)]
    columns: dict[Role, int] = {}
    english = False
    for position, name in enumerate(names):
        found = _role_of(name)
        if found is not None and found[0] not in columns:
            columns[found[0]] = position
            english = english or (found[0] is Role.DATE and found[1])
    if not all(role in columns for role in REQUIRED) or not any(role in columns for role in AMOUNT_ROLES):
        return None
    return Header(line=index, separator=separator, columns=columns, english=english)


def _header_name(cell: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", fold(cell)).split())


def _role_of(name: str) -> tuple[Role, bool] | None:
    """The column's role and whether its header is English; an exact name wins over a prefix («monto usd»)."""
    for exact in (True, False):
        for english, vocabulary in ((False, SPANISH_HEADERS), (True, ENGLISH_HEADERS)):
            for role, synonyms in vocabulary.items():
                if any(name == synonym if exact else name.startswith(synonym + " ") for synonym in synonyms):
                    return role, english
    return None


def _data_lines(lines: Sequence[str], header: Header) -> Iterable[tuple[int, str]]:
    for index in range(header.line + 1, len(lines)):
        line = lines[index]
        cells = _cells(line, header.separator)
        if not any(cells):
            continue
        if _BALANCE_ROW.match(_header_name(_cell(cells, header, Role.DESCRIPTION))):
            continue
        yield index + 1, line


def _cell(cells: Sequence[str], header: Header, role: Role) -> str:
    position = header.columns.get(role)
    return cells[position] if position is not None and position < len(cells) else ""


def _movement(
    position: int,
    number: int,
    line: str,
    cells: Sequence[str],
    header: Header,
    order: DateOrder,
    default_currency: str,
) -> StatementMovement:
    booked_on = _parse_date(_cell(cells, header, Role.DATE), order)
    amount, amount_problem = _amount(cells, header)
    problems = [
        *([f"No se pudo leer la fecha «{_cell(cells, header, Role.DATE)}»."] if booked_on is None else []),
        *([amount_problem] if amount_problem else []),
    ]
    currency = _cell(cells, header, Role.CURRENCY).upper()
    return StatementMovement(
        id=f"m{position:03d}",
        row=number,
        booked_on=booked_on,
        description=_cell(cells, header, Role.DESCRIPTION),
        amount=amount,
        currency=currency if _CURRENCY_CODE.match(currency) else default_currency,
        reference=_cell(cells, header, Role.REFERENCE) or None,
        quote=line.strip(),
        read=not problems,
        unread_reason=" ".join(problems) or None,
    )


def _amount(cells: Sequence[str], header: Header) -> tuple[Decimal | None, str | None]:
    if Role.AMOUNT in header.columns:
        return _signed(_cell(cells, header, Role.AMOUNT))
    debit, credit = (_nonzero(_cell(cells, header, role)) for role in (Role.DEBIT, Role.CREDIT))
    if debit and credit:
        return None, f"La fila trae cargo «{debit}» y abono «{credit}» a la vez; no se elige uno."
    if not debit and not credit:
        return None, "La fila no trae monto."
    amount, problem = _signed(debit or credit)
    if amount is None:
        return None, problem
    return (-abs(amount) if debit else abs(amount)), None


def _nonzero(cell: str) -> str:
    """A debit or credit cell, empty when it reads as zero: banks write «0,00» in the column that does not apply."""
    amount, _ = _signed(cell)
    return "" if amount == 0 else cell


def _signed(cell: str) -> tuple[Decimal | None, str | None]:
    words = [word for word in _WORD.findall(_CURRENCY_SYMBOLS.sub("", cell)) if not _CURRENCY_CODE.match(word)]
    if words:  # «50,00 DB» is an outflow: a marker the code does not read never leaves a positive amount behind
        return None, f"El monto «{cell}» trae «{' '.join(words)}» junto al número; no se adivina su signo."
    try:
        return parse_signed_amount(cell), None
    except AmountFormatError:
        return None, f"No se pudo leer el monto «{cell}»."


def _date_order(cells: Sequence[str], *, english: bool) -> tuple[DateOrder, list[str]]:
    parts = [(int(match[1]), int(match[2])) for cell in cells if (match := _NUMERIC_DATE.match(_date_text(cell)))]
    if any(first > MONTHS_IN_YEAR for first, _ in parts):
        return DateOrder.DAY_FIRST, []
    if any(second > MONTHS_IN_YEAR for _, second in parts):
        return DateOrder.MONTH_FIRST, []
    order = DateOrder.MONTH_FIRST if english else DateOrder.DAY_FIRST
    if not parts:
        return order, []
    return order, [f"Ninguna fecha del archivo decide el orden; se leyeron como {order.value}/año."]


def _date_text(cell: str) -> str:
    return cell.split()[0] if cell.split() else ""


def _parse_date(cell: str, order: DateOrder) -> date | None:
    text = _date_text(cell)
    if match := _ISO_DATE.match(text):
        return _date(int(match[1]), int(match[2]), int(match[3]))
    if match := _NUMERIC_DATE.match(text):
        first, second, year = int(match[1]), int(match[2]), int(match[3])
        year = year + CENTURY if year < CENTURY else year
        day, month = (first, second) if order is DateOrder.DAY_FIRST else (second, first)
        return _date(year, month, day)
    written = dates_in(cell)
    return next(iter(written)) if len(written) == 1 else None


def _date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None
