"""What every rendering of an invoice shows, written the way a Colombian supplier would write it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from custodio.contracts import InvoiceSpec
from custodio.extraction.amounts import format_amount

TITLE = "FACTURA ELECTRÓNICA DE VENTA"
GREETING = "Buenos días, le comparto la factura de este mes."


@dataclass(frozen=True)
class InvoiceContent:
    supplier: str
    tax_line: str
    number: str
    issue_line: str
    due_line: str | None
    description: str
    amount_text: str
    bank_lines: tuple[str, ...]
    note: str | None
    hidden_text: str | None


def content_of(spec: InvoiceSpec) -> InvoiceContent:
    """`spec.amount_text`, when present, is shown exactly as written and no currency code is added anywhere."""
    return InvoiceContent(
        supplier=spec.supplier_name,
        tax_line=f"{spec.tax_label} {spec.supplier_tax_id}",
        number=spec.invoice_number,
        issue_line=f"Fecha de emisión: {_day_first(spec.issue_date)}",
        due_line=f"Fecha de vencimiento: {_day_first(spec.due_date)}" if spec.due_date else None,
        description=spec.description,
        amount_text=spec.amount_text or format_amount(spec.amount, spec.currency),
        bank_lines=(
            f"Banco: {spec.bank_name}",
            f"Cuenta No. {spec.account_number}",
            f"Titular: {spec.supplier_name}",
        ),
        note=spec.note,
        hidden_text=spec.hidden_text,
    )


def _day_first(day: date) -> str:
    return day.strftime("%d/%m/%Y")
