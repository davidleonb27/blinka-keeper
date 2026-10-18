"""What a bank statement says, what Blinka Keeper paid, and how code paired them.

A movement's amount is signed in the account's terms: negative is money that left the account. Every match carries
its level and a Spanish reason with the figures, so a person (or an accountant) can redo it by hand.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import Field

from custodio.contracts import Amount, DecisionStatus, Model, Ratio


class StatementMovement(Model):
    id: str  # "m001", in the order the statement lists them
    row: int  # 1-based: the line of the CSV file, or the position in a document's reading
    booked_on: date | None
    description: str
    amount: Amount | None  # signed, in `currency`; None when it could not be read
    currency: str | None
    reference: str | None = None
    quote: str  # the row exactly as the statement writes it
    read: bool  # set by code: the date and the amount were read and, for documents, found in the quote
    unread_reason: str | None = None  # Spanish, why it is NO LEÍDO


class Statement(Model):
    movements: list[StatementMovement]
    reader: str  # "csv", or the pipeline that read a document, e.g. "pdfplumber+claude-sonnet-5-5"
    currency: str  # the account's currency, used where a row names none
    warnings: list[str] = Field(default_factory=list)


class MatchSettings(Model):
    """Explicit and shown to the person: nothing is reconciled under a tolerance nobody can see."""

    date_window_days: int = Field(default=3, ge=0, le=15)
    fx_tolerance_pct: Ratio = Field(default=Decimal("0.5"), ge=0, le=5)  # only for payments made in another currency
    max_split_parts: int = Field(default=4, ge=2, le=6)


class PaidInvoice(Model):
    """A payment Blinka Keeper made (alone or approved by a person), as reconciliation needs it."""

    invoice_id: str
    invoice_number: str | None
    supplier_name: str | None
    names: list[str]  # registered name, aliases and the name on the invoice
    tax_id: str | None = None
    amount: Amount  # as invoiced
    currency: str
    amount_base: Amount
    base_currency: str
    paid_on: date
    external_id: str | None = None  # the rail's id, e.g. a Stripe transfer "tr_…"
    dashboard_url: str | None = None
    acta_url: str


class UnpaidInvoice(Model):
    """An invoice Blinka Keeper did not pay; an outflow that matches it is still an outflow nobody authorized."""

    invoice_id: str
    invoice_number: str | None
    supplier_name: str | None
    names: list[str]
    amount: Amount
    currency: str
    amount_base: Amount
    base_currency: str
    status: DecisionStatus


class MovementStatus(StrEnum):
    RECONCILED = "reconciled"
    RECONCILED_WITH_DIFFERENCE = "reconciled_with_difference"
    UNMATCHED_OUTFLOW = "unmatched_outflow"  # money left with no invoice Blinka Keeper paid: red alert
    BANK_FEE = "bank_fee"
    DUPLICATE = "duplicate"  # the same movement listed again
    UNREAD = "unread"  # NO LEÍDO: never interpreted, a person reads it
    INFLOW = "inflow"  # money in (or no money out): outside accounts payable


# What a person must review before the month can close: money out that no paid invoice explains.
NEEDS_REVIEW = frozenset({MovementStatus.UNMATCHED_OUTFLOW, MovementStatus.DUPLICATE, MovementStatus.UNREAD})


class MatchLevel(StrEnum):
    EXACT = "exact"  # a reference (transfer id, invoice number, acta) and the exact amount
    AMOUNT_DATE = "amount_date"  # exact amount, date within the window and the beneficiary named
    SPLIT = "split"  # several movements that add up exactly to one payment
    TOLERANCE = "tolerance"  # within the explicit FX tolerance


class MovementResult(Model):
    movement_id: str
    status: MovementStatus
    level: MatchLevel | None = None
    invoice_id: str | None = None
    allocated: Amount = Decimal(0)  # how much of the movement the match accounts for; never more than the movement
    difference: Amount | None = None  # bank amount minus the payment, in the movement's currency
    duplicate_of: str | None = None
    reason: str  # Spanish, with the figures


class PaymentStatus(StrEnum):
    CONFIRMED = "confirmed"  # the bank shows it
    PENDING = "pending"  # not in this statement yet


class PaymentResult(Model):
    invoice_id: str
    invoice_number: str | None
    supplier_name: str | None
    paid_on: date
    expected: Amount | None  # what the statement should show, in its currency; None if the currencies cannot meet
    currency: str
    status: PaymentStatus
    level: MatchLevel | None = None
    movement_ids: list[str] = Field(default_factory=list)
    difference: Amount | None = None
    external_id: str | None = None
    dashboard_url: str | None = None
    acta_url: str
    reason: str


class ReconciliationOutcome(Model):
    movements: list[MovementResult]  # in the statement's order
    payments: list[PaymentResult]  # by invoice id
    settings: MatchSettings


STATUS_LABELS: dict[MovementStatus, str] = {
    MovementStatus.RECONCILED: "Conciliado",
    MovementStatus.RECONCILED_WITH_DIFFERENCE: "Conciliado con diferencia",
    MovementStatus.UNMATCHED_OUTFLOW: "Salida sin factura",
    MovementStatus.BANK_FEE: "Comisión bancaria",
    MovementStatus.DUPLICATE: "Duplicado",
    MovementStatus.UNREAD: "NO LEÍDO",
    MovementStatus.INFLOW: "Ingreso",
}
LEVEL_LABELS: dict[MatchLevel, str] = {
    MatchLevel.EXACT: "Exacto",
    MatchLevel.AMOUNT_DATE: "Por monto y fecha",
    MatchLevel.SPLIT: "Partido",
    MatchLevel.TOLERANCE: "Con tolerancia",
}


class Review(Model):
    """A person looked at a movement that needed it and wrote down what it is. Stays in the ledger."""

    movement_id: str
    reviewer: str
    note: str
    at: datetime
    ledger_seq: int


class PeriodClose(Model):
    period: str  # "2026-10"
    closed_at: datetime
    closed_by: str
    reconciliation_id: str
    ledger_seq: int
    ledger_hash: str


class Tally(Model):
    count: int = 0
    total: Amount = Decimal(0)


class PeriodSummary(Model):
    """The month in figures, in the account's currency. `alerts_open` must be zero to close it."""

    currency: str
    paid: Tally
    held: Tally
    rejected: Tally
    pending_approval: Tally
    reconciled: Tally  # movements, by what they reconcile
    differences: Tally  # payments reconciled with an FX difference, by the sum of the differences
    fees: Tally
    inflows: Tally
    unexplained: Tally  # outflows no paid invoice explains, duplicates included
    pending_in_bank: Tally  # payments that do not appear in the statement yet
    alerts: int  # movements a person must review
    alerts_open: int
