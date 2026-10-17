"""Small builders for statement movements and invoices, so each test states only what it is about."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from custodio.contracts import DecisionStatus
from custodio.reconciliation.models import PaidInvoice, StatementMovement, UnpaidInvoice

OCTOBER = 10
YEAR = 2026


def day(number: int) -> date:
    return date(YEAR, OCTOBER, number)


def movement(
    movement_id: str,
    amount: str | None,
    description: str,
    *,
    on: int = 16,
    reference: str | None = None,
    currency: str = "USD",
    read: bool = True,
) -> StatementMovement:
    return StatementMovement(
        id=movement_id,
        row=int(movement_id.removeprefix("m") or 0),
        booked_on=day(on),
        description=description,
        amount=Decimal(amount) if amount is not None else None,
        currency=currency,
        reference=reference,
        quote=f"{day(on).isoformat()};{description};{amount}",
        read=read,
        unread_reason=None if read else "No se pudo leer el monto.",
    )


def paid(
    invoice_id: str,
    number: str | None,
    name: str,
    amount: str,
    *,
    currency: str = "USD",
    amount_base: str | None = None,
    on: int = 16,
    external_id: str | None = None,
) -> PaidInvoice:
    return PaidInvoice(
        invoice_id=invoice_id,
        invoice_number=number,
        supplier_name=name,
        names=[name],
        amount=Decimal(amount),
        currency=currency,
        amount_base=Decimal(amount_base or amount),
        base_currency="USD",
        paid_on=day(on),
        external_id=external_id,
        acta_url=f"https://custodio.test/acta/{invoice_id}",
    )


def unpaid(
    invoice_id: str, number: str, name: str, amount: str, status: DecisionStatus = DecisionStatus.PENDING_APPROVAL
) -> UnpaidInvoice:
    return UnpaidInvoice(
        invoice_id=invoice_id,
        invoice_number=number,
        supplier_name=name,
        names=[name],
        amount=Decimal(amount),
        currency="USD",
        amount_base=Decimal(amount),
        base_currency="USD",
        status=status,
    )
