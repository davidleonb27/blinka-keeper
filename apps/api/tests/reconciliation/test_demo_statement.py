"""The demo statement (CSV and PDF in the dataset) tells the story of the demo batch, hard cases included."""

import io
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

import pdfplumber
import pytest

from custodio import dataset, engine
from custodio.contracts import DecisionStatus
from custodio.reconciliation.csv_statement import read_csv_statement
from custodio.reconciliation.demo import (
    DEMO_PDF_PATH,
    demo_payment_day,
    demo_statement_csv,
    demo_statement_pdf,
    shift_for,
)
from custodio.reconciliation.document_statement import (
    RowReading,
    StatementReading,
    read_statement_document,
    verified_statement,
)
from custodio.reconciliation.match import reconcile
from custodio.reconciliation.models import (
    MatchLevel,
    MatchSettings,
    MovementResult,
    MovementStatus,
    PaidInvoice,
    PaymentStatus,
    ReconciliationOutcome,
    StatementMovement,
    UnpaidInvoice,
)

PAID = (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN)


def demo_batch(paid_on: date) -> tuple[list[PaidInvoice], list[UnpaidInvoice]]:
    state, policy = dataset.demo_company()
    cases = dataset.demo_cases()
    batch = engine.decide_all(cases, state, policy)
    numbers = {case.id: case.extraction.invoice_number.value for case in cases}
    paid, unpaid = [], []
    for decision in batch.decisions:
        assert decision.amount is not None and decision.currency and decision.amount_base is not None
        common = {
            "invoice_id": decision.invoice_id,
            "invoice_number": numbers[decision.invoice_id],
            "supplier_name": decision.supplier_name,
            "names": [decision.supplier_name or ""],
            "amount": decision.amount,
            "currency": decision.currency,
            "amount_base": decision.amount_base,
            "base_currency": policy.base_currency,
        }
        if decision.status in PAID:
            paid.append(PaidInvoice(**common, paid_on=paid_on, acta_url=f"https://c.test/acta/{decision.invoice_id}"))
        else:
            unpaid.append(UnpaidInvoice(**common, status=decision.status))
    return paid, unpaid


def outcome_for(movements: list[StatementMovement], paid_on: date) -> ReconciliationOutcome:
    paid, unpaid = demo_batch(paid_on)
    return reconcile(movements, paid, unpaid, MatchSettings())


def csv_movements(shift: int = 0) -> list[StatementMovement]:
    return read_csv_statement(demo_statement_csv(shift), default_currency="USD").movements


def by_description(
    outcome: ReconciliationOutcome, movements: list[StatementMovement], text: str
) -> list[MovementResult]:
    ids = [movement.id for movement in movements if text in movement.description]
    return [item for item in outcome.movements if item.movement_id in ids]


def test_every_row_of_the_demo_csv_is_read() -> None:
    movements = csv_movements()

    assert len(movements) == 22
    assert all(movement.read for movement in movements)


def test_the_demo_statement_reconciles_the_demo_batch_with_every_hard_case() -> None:
    movements = csv_movements()
    outcome = outcome_for(movements, demo_payment_day())

    levels = Counter((item.status, item.level) for item in outcome.movements)
    assert levels == {
        (MovementStatus.RECONCILED, MatchLevel.EXACT): 9,
        (MovementStatus.RECONCILED, MatchLevel.SPLIT): 2,
        (MovementStatus.RECONCILED, MatchLevel.AMOUNT_DATE): 2,
        (MovementStatus.RECONCILED_WITH_DIFFERENCE, MatchLevel.TOLERANCE): 4,
        (MovementStatus.BANK_FEE, None): 2,
        (MovementStatus.DUPLICATE, None): 1,
        (MovementStatus.UNMATCHED_OUTFLOW, None): 1,
        (MovementStatus.INFLOW, None): 1,
    }
    (orbit,) = by_description(outcome, movements, "ORBIT")
    assert "F-018" in orbit.reason
    (pixel,) = by_description(outcome, movements, "PIXEL")
    assert "PN-1201" in pixel.reason
    pending = [payment.invoice_id for payment in outcome.payments if payment.status is PaymentStatus.PENDING]
    assert pending == ["F-036"]


def test_the_demo_statement_moves_to_the_day_the_batch_was_paid() -> None:
    later = demo_payment_day() + timedelta(days=5)

    movements = csv_movements(shift_for(later))
    outcome = outcome_for(movements, later)

    assert min(m.booked_on for m in movements if m.booked_on) == date(2026, 10, 14) + timedelta(days=5)
    assert sum(item.invoice_id is not None for item in outcome.movements) == 17
    assert shift_for(None) == 0


def test_the_pdf_in_the_dataset_is_the_one_the_code_renders() -> None:
    assert DEMO_PDF_PATH.read_bytes() == demo_statement_pdf()


def pdf_text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as document:
        return "\n".join(page.extract_text() or "" for page in document.pages)


def test_the_pdf_lists_the_same_movements_as_the_csv_on_one_line_each() -> None:
    text = pdf_text(demo_statement_pdf())
    movements = csv_movements()
    rows = []
    for movement in movements:
        assert movement.booked_on is not None
        written = movement.booked_on.strftime("%d/%m/%Y")
        (line,) = {line for line in text.splitlines() if movement.description in line and written in line}
        rows.append(
            RowReading(
                quote=line,
                booked_on=movement.booked_on.isoformat() if movement.booked_on else None,
                description=movement.description,
                reference=movement.reference,
                amount=str(movement.amount),
                currency=None,
            )
        )

    statement = verified_statement(
        StatementReading(account_currency="USD", rows=rows), text, default_currency="USD", reader="test"
    )

    read = [(m.booked_on, m.amount, m.description) for m in statement.movements]
    assert read == [(m.booked_on, m.amount, m.description) for m in movements]
    assert all(m.read for m in statement.movements)


@pytest.mark.live
def test_claude_reads_the_demo_pdf_like_the_csv() -> None:
    statement = read_statement_document(
        demo_statement_pdf(), filename="extracto.pdf", media_type="application/pdf", default_currency="USD"
    )

    expected = Counter((m.booked_on, m.amount) for m in csv_movements())
    assert Counter((m.booked_on, m.amount) for m in statement.movements if m.read) == expected
    assert all(m.read for m in statement.movements)
    assert statement.currency == "USD"
    assert sum(m.amount for m in statement.movements if m.amount) == Decimal("-17847.93")
