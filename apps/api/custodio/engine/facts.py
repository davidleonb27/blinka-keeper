"""What the engine knows about an invoice and the charges around it.

Facts come only from the extraction and the received time; `InvoiceCase.expected` and `InvoiceCase.trap` are never
read here or anywhere in the decision path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from custodio.contracts import InvoiceCase, PaymentRecord
from custodio.engine.units import as_utc, parse_amount, to_base


@dataclass(frozen=True)
class InvoiceFacts:
    case_id: str
    position: int  # index in the input, the tie-breaker for invoices received at the same instant
    received_at: datetime  # UTC
    supplier_name: str | None
    supplier_tax_id: str | None
    invoice_number: str | None
    amount: Decimal | None
    currency: str | None
    account_number: str | None
    amount_base: Decimal | None

    @property
    def received_on(self) -> date:
        return self.received_at.date()

    @property
    def arrival(self) -> tuple[datetime, int]:
        return (self.received_at, self.position)


@dataclass(frozen=True)
class Charge:
    """An invoice of the same supplier seen before or around this one: from history (always paid) or this batch."""

    invoice_id: str
    invoice_number: str | None
    amount: Decimal | None
    currency: str | None
    amount_base: Decimal | None
    on: date
    paid: bool


def read_facts(case: InvoiceCase, position: int, fx: Mapping[str, Decimal]) -> InvoiceFacts:
    extraction = case.extraction
    amount = parse_amount(extraction.amount.value)
    currency = _upper(extraction.currency.value)
    return InvoiceFacts(
        case_id=case.id,
        position=position,
        received_at=as_utc(case.received_at),
        supplier_name=extraction.supplier_name.value,
        supplier_tax_id=extraction.supplier_tax_id.value,
        invoice_number=extraction.invoice_number.value,
        amount=amount,
        currency=currency,
        account_number=extraction.account_number.value,
        amount_base=to_base(amount, currency, fx),
    )


def charge_from_invoice(facts: InvoiceFacts, *, paid: bool) -> Charge:
    return Charge(
        invoice_id=facts.case_id,
        invoice_number=facts.invoice_number,
        amount=facts.amount,
        currency=facts.currency,
        amount_base=facts.amount_base,
        on=facts.received_on,
        paid=paid,
    )


def charge_from_history(record: PaymentRecord) -> Charge:
    return Charge(
        invoice_id=record.invoice_id,
        invoice_number=record.invoice_number,
        amount=record.amount,
        currency=_upper(record.currency),
        amount_base=record.amount_base,
        on=record.paid_on,
        paid=True,
    )


def _upper(currency: str | None) -> str | None:
    return currency.strip().upper() if currency and currency.strip() else None
