"""The demo bank statement: Cobalto Labs' October in its bank, written as the bank would export it.

`statement_demo.csv` in the dataset is the single source; the PDF is drawn from the same rows with reportlab and
kept next to it (`python -m custodio.reconciliation.demo` rewrites it). Both are dated for the demo world, where the
batch is paid on the demo company's `today`. A workspace pays its batch on the day a visitor decides it, so the
statement it is offered moves by the same number of days; nothing else changes.

The story: the payments Blinka Keeper made, one split in two transfers, four with cents of FX difference, one whose
reference misspells the invoice number, one the bank lists twice, one that is not in the statement yet, two bank
charges, a customer's deposit, and a transfer to a supplier whose invoice was waiting for approval.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from importlib.resources import files
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from custodio.dataset import demo_company

DEMO_CSV = "statement_demo.csv"
DEMO_PDF = "statement_demo.pdf"
DEMO_PDF_PATH = Path(str(files("custodio.dataset").joinpath(DEMO_PDF)))
SEPARATOR = ";"
DATE_FORMAT = "%d/%m/%Y"
_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")

PAGE_WIDTH, PAGE_HEIGHT = float(letter[0]), float(letter[1])
MARGIN = 48.0
RIGHT = PAGE_WIDTH - MARGIN
BODY_FONT, BOLD_FONT = "Helvetica", "Helvetica-Bold"
TITLE_SIZE, BODY_SIZE, SMALL_SIZE = 15.0, 8.5, 7.0
ROW = 15.0
COLUMN_DESCRIPTION, COLUMN_REFERENCE, COLUMN_AMOUNT = MARGIN + 62, MARGIN + 290, RIGHT - 80
INK = (0.13, 0.14, 0.17)
MUTED = (0.42, 0.44, 0.48)
BRAND = (0.07, 0.24, 0.42)
FOOTER = "Extracto de demostración: datos sintéticos de Blinka Keeper. Ninguna cuenta ni movimiento es real."


@dataclass(frozen=True)
class _Row:
    on: str
    description: str
    reference: str
    amount: str
    balance: str


def demo_payment_day() -> date:
    """The day the demo world pays its batch: the demo company's `today`."""
    state, _ = demo_company()
    return state.today


def shift_for(first_payment: date | None) -> int:
    """Days to move the demo statement so it follows a batch paid on `first_payment` (none paid yet: none)."""
    return 0 if first_payment is None else (first_payment - demo_payment_day()).days


def demo_statement_csv(shift: int = 0) -> bytes:
    lines = files("custodio.dataset").joinpath(DEMO_CSV).read_text(encoding="utf-8").splitlines()
    return ("\n".join(_shifted(line, shift) for line in lines) + "\n").encode()


def demo_statement_pdf(shift: int = 0) -> bytes:
    preamble, rows = _parsed(demo_statement_csv(shift).decode())
    buffer = io.BytesIO()
    page = Canvas(buffer, pagesize=letter, invariant=1)
    page.setTitle("Extracto de cuenta corriente")
    page.setAuthor("Banco Andino")
    y = _draw_header(page, preamble, rows)
    for row in rows:
        y = _draw_row(page, row, y)
    page.setFont(BODY_FONT, SMALL_SIZE)
    page.setFillColorRGB(*MUTED)
    page.drawString(MARGIN, MARGIN, FOOTER)
    page.showPage()
    page.save()
    return buffer.getvalue()


def _shifted(line: str, shift: int) -> str:
    cells = line.split(SEPARATOR)
    if not cells or not _DATE.match(cells[0]):
        return line
    moved = datetime.strptime(cells[0], DATE_FORMAT).date() + timedelta(days=shift)
    return SEPARATOR.join([moved.strftime(DATE_FORMAT), *cells[1:]])


def _parsed(text: str) -> tuple[list[list[str]], list[_Row]]:
    preamble: list[list[str]] = []
    rows: list[_Row] = []
    for cells in csv.reader(text.splitlines(), delimiter=SEPARATOR):
        if cells and _DATE.match(cells[0]):
            on, description, reference, amount, _, balance = cells
            rows.append(_Row(on, description, reference, amount, balance))
        elif cells and cells[0] != "Fecha":
            preamble.append(cells)
    return preamble, rows


def _draw_header(page: Canvas, preamble: list[list[str]], rows: list[_Row]) -> float:
    title, *details = preamble
    page.setFillColorRGB(*BRAND)
    page.setFont(BOLD_FONT, TITLE_SIZE)
    page.drawString(MARGIN, PAGE_HEIGHT - MARGIN - 10, "BANCO ANDINO")
    page.setFillColorRGB(*INK)
    page.setFont(BODY_FONT, BODY_SIZE)
    y = PAGE_HEIGHT - MARGIN - 30
    page.drawString(MARGIN, y, title[0])
    for cells in details:
        y -= ROW
        page.drawString(MARGIN, y, f"{cells[0]}: {cells[1]}")
    y -= ROW
    page.drawString(MARGIN, y, f"Periodo: {rows[0].on} al {rows[-1].on}")
    y -= ROW * 1.6
    page.setFont(BOLD_FONT, BODY_SIZE)
    page.drawString(MARGIN, y, "Fecha")
    page.drawString(COLUMN_DESCRIPTION, y, "Descripción")
    page.drawString(COLUMN_REFERENCE, y, "Referencia")
    page.drawRightString(COLUMN_AMOUNT, y, "Monto USD")
    page.drawRightString(RIGHT, y, "Saldo USD")
    page.setStrokeColorRGB(*MUTED)
    page.line(MARGIN, y - 4, RIGHT, y - 4)
    page.setFont(BODY_FONT, BODY_SIZE)
    return y - ROW


def _draw_row(page: Canvas, row: _Row, y: float) -> float:
    page.drawString(MARGIN, y, row.on)
    page.drawString(COLUMN_DESCRIPTION, y, row.description.upper())
    page.drawString(COLUMN_REFERENCE, y, row.reference)
    page.drawRightString(COLUMN_AMOUNT, y, row.amount)
    page.drawRightString(RIGHT, y, row.balance)
    return y - ROW


if __name__ == "__main__":
    DEMO_PDF_PATH.write_bytes(demo_statement_pdf())
