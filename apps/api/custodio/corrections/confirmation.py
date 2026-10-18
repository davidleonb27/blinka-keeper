"""A supplier's typed confirmation becomes a corrected invoice text that goes through the same reader and rules.

Only well-formed values are taken (an amount, an ISO currency, an invoice number, a date): free text cannot ride in.
Every other datum, the account included, is the original reading's, so a confirmation can never change where the
money goes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from custodio.contracts import ExtractedInvoice
from custodio.corrections.models import CorrectableField
from custodio.extraction.amounts import parse_amount
from custodio.extraction.errors import AmountFormatError

MAX_CONFIRMED_LENGTH = 30
CURRENCY_CODE = re.compile(r"[A-Z]{3}")
INVOICE_NUMBER = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_/.#]*")
AMOUNT_CHARACTERS = re.compile(r"[\d.,' ]+")
CENTS = Decimal("0.01")
HEADER = "Factura corregida por el proveedor"


class ConfirmationInvalid(ValueError):
    """A typed value that is not what its field takes; the message is Spanish, for the supplier."""


def corrected_text(original: ExtractedInvoice, confirmed: Mapping[CorrectableField, str]) -> str:
    values = {name: _clean(name, value) for name, value in confirmed.items()}

    def pick(name: CorrectableField) -> str:
        return values.get(name) or getattr(original, name.value).value or ""

    lines = (
        ("Proveedor", original.supplier_name.value),
        ("Identificación tributaria", original.supplier_tax_id.value),
        ("Número de factura", pick(CorrectableField.INVOICE_NUMBER)),
        ("Fecha de emisión", pick(CorrectableField.ISSUE_DATE)),
        ("Vence", original.due_date.value),
        ("Monto", pick(CorrectableField.AMOUNT)),
        ("Moneda", pick(CorrectableField.CURRENCY)),
        ("Banco", original.bank_name.value),
        ("Cuenta", original.account_number.value),
        ("Concepto", original.description.value),
    )
    return "\n".join([HEADER, *(f"{label}: {value}" for label, value in lines if value)])


def _clean(name: CorrectableField, raw: str) -> str:
    value = raw.strip()
    if not value or len(value) > MAX_CONFIRMED_LENGTH or "\n" in value:
        raise ConfirmationInvalid(f"El valor de «{LABELS[name]}» no es válido.")
    return CLEANERS[name](value)


def _amount(value: str) -> str:
    if not AMOUNT_CHARACTERS.fullmatch(value):
        raise ConfirmationInvalid("El monto sólo lleva números, puntos y comas.")
    try:
        amount = parse_amount(value)
    except AmountFormatError as error:
        raise ConfirmationInvalid("El monto no es un número válido.") from error
    if amount <= 0:
        raise ConfirmationInvalid("El monto debe ser mayor que cero.")
    return str(amount.quantize(CENTS))


def _currency(value: str) -> str:
    code = value.upper()
    if not CURRENCY_CODE.fullmatch(code):
        raise ConfirmationInvalid("La moneda va con su código de tres letras, por ejemplo USD o COP.")
    return code


def _invoice_number(value: str) -> str:
    if not INVOICE_NUMBER.fullmatch(value):
        raise ConfirmationInvalid("El número de factura sólo lleva letras, números y separadores (- _ / . #).")
    return value


def _issue_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ConfirmationInvalid("La fecha va como AAAA-MM-DD.") from error


LABELS = {
    CorrectableField.AMOUNT: "monto",
    CorrectableField.CURRENCY: "moneda",
    CorrectableField.INVOICE_NUMBER: "número de factura",
    CorrectableField.ISSUE_DATE: "fecha de emisión",
}
CLEANERS = {
    CorrectableField.AMOUNT: _amount,
    CorrectableField.CURRENCY: _currency,
    CorrectableField.INVOICE_NUMBER: _invoice_number,
    CorrectableField.ISSUE_DATE: _issue_date,
}
