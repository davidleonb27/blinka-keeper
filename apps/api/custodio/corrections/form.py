"""Form checks the fifteen rules do not cover: a missing invoice number, an impossible date, a total that does not add
up. They never stop a payment on their own; they join the request when an invoice is already stopped, so the supplier
fixes everything in one round."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from custodio.contracts import ExtractedInvoice
from custodio.corrections.models import CorrectableField, Issue, IssueKind
from custodio.extraction.amounts import amounts_in
from custodio.extraction.text import fold

CENT = Decimal("0.01")
_SUBTOTAL = re.compile(r"^\s*(sub\s*total|base gravable)\b")
_TAX = re.compile(r"^\s*(iva|impuestos?|tax|vat|igv)\b")
_DEDUCTION = re.compile(r"^\s*(retencion|retefuente|reteiva|descuento)\b")
_TOTAL = re.compile(r"^\s*total\b")


def form_issues(extraction: ExtractedInvoice, received_on: date) -> list[Issue]:
    found = [_missing_number(extraction), _invalid_date(extraction, received_on), _total_mismatch(extraction)]
    return [issue for issue in found if issue is not None]


def _missing_number(extraction: ExtractedInvoice) -> Issue | None:
    if (extraction.invoice_number.value or "").strip():
        return None
    return Issue(
        kind=IssueKind.MISSING_INVOICE_NUMBER,
        rule_id=None,
        fields=[CorrectableField.INVOICE_NUMBER],
        problem="La factura no trae un número de factura.",
        expected="un número de factura único, el mismo que figura en su contabilidad",
    )


def _invalid_date(extraction: ExtractedInvoice, received_on: date) -> Issue | None:
    problem = _date_problem(extraction.issue_date.value, extraction.due_date.value, received_on)
    if problem is None:
        return None
    return Issue(
        kind=IssueKind.INVALID_DATE,
        rule_id=None,
        fields=[CorrectableField.ISSUE_DATE],
        problem=problem,
        expected="una fecha de emisión real (AAAA-MM-DD), no posterior al día en que se envía ni al vencimiento",
    )


def _date_problem(issued: str | None, due: str | None, received_on: date) -> str | None:
    if not issued:
        return "La factura no trae la fecha de emisión."
    issue_date = _parse(issued)
    if issue_date is None:
        return "La fecha de emisión no es una fecha válida."
    if issue_date > received_on:
        return "La fecha de emisión es posterior al día en que llegó la factura."
    due_date = _parse(due) if due else None
    if due_date is not None and issue_date > due_date:
        return "La fecha de emisión es posterior a la fecha de vencimiento."
    return None


def _parse(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _total_mismatch(extraction: ExtractedInvoice) -> Issue | None:
    subtotal, taxes, deductions, total = _figures(extraction.visible_text)
    if subtotal is None or total is None:
        return None
    if abs(subtotal + taxes - deductions - total) < CENT:
        return None
    return Issue(
        kind=IssueKind.TOTAL_MISMATCH,
        rule_id=None,
        fields=[],
        problem="El subtotal, los impuestos y las retenciones de la factura no suman el total que cobra.",
        expected="una factura cuyo total sea la suma de sus conceptos, impuestos y retenciones",
    )


def _figures(text: str) -> tuple[Decimal | None, Decimal, Decimal, Decimal | None]:
    subtotal: Decimal | None = None
    total: Decimal | None = None
    taxes = deductions = Decimal(0)
    for line in text.splitlines():
        folded = fold(line)
        amount = _last_amount(line)
        if amount is None:
            continue
        if _SUBTOTAL.search(folded):
            subtotal = amount
        elif _TAX.search(folded):
            taxes += amount
        elif _DEDUCTION.search(folded):
            deductions += amount
        elif _TOTAL.search(folded):
            total = amount
    return subtotal, taxes, deductions, total


def _last_amount(line: str) -> Decimal | None:
    amounts = amounts_in(line.partition(":")[2] or line)
    return amounts[-1] if amounts else None
