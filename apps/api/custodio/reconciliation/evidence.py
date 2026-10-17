"""The evidence pack for the accountant: one ZIP per closed month.

Reproducible on purpose: the same state gives the same bytes. Entries are written in a fixed order with a fixed
timestamp, JSON with sorted keys, the PDF in reportlab's invariant mode. The one thing that changes between two
downloads is `generado_en` in `manifiesto.json`, which also lists the SHA-256 of every other file.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.resources import files
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

from custodio.contracts import LedgerEntry, LedgerVerification, Model
from custodio.engine.formatting import counted, day_month, money, month_name, plus_minus_percent
from custodio.engine.ledger import canonical_json
from custodio.reconciliation.models import (
    LEVEL_LABELS,
    NEEDS_REVIEW,
    STATUS_LABELS,
    PaymentStatus,
    PeriodClose,
    PeriodSummary,
    ReconciliationOutcome,
    Review,
    Statement,
    Tally,
)

MANIFEST = "manifiesto.json"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)  # the earliest a ZIP can store: the entries' own dates never vary
UNIX_FILE = 3
FILE_MODE = 0o644 << 16
COMPRESSION_LEVEL = 9
VERIFIER = "ledger_verifier.py"
CSV_COLUMNS = (
    "fila",
    "fecha",
    "descripcion",
    "referencia",
    "monto",
    "moneda",
    "estado",
    "nivel",
    "factura",
    "conciliado",
    "diferencia",
    "duplicado_de",
    "razon",
    "revisado_por",
    "nota_revision",
)

PAGE_WIDTH, PAGE_HEIGHT = float(letter[0]), float(letter[1])
MARGIN = 54.0
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN
FIGURES = PAGE_WIDTH - MARGIN
BODY_FONT, BOLD_FONT = "Helvetica", "Helvetica-Bold"
TITLE_SIZE, HEADING_SIZE, BODY_SIZE, SMALL_SIZE = 17.0, 11.5, 9.5, 8.0
LINE = 14.0
INK = (0.13, 0.14, 0.17)
MUTED = (0.42, 0.44, 0.48)
BRAND = (0.07, 0.24, 0.42)


class EvidenceSource(Model):
    company_name: str
    period: str
    statement: Statement
    outcome: ReconciliationOutcome
    reviews: list[Review]
    summary: PeriodSummary
    actas: dict[str, dict[str, Any]]  # invoice id → the acta as the API serves it
    ledger: list[LedgerEntry]
    verification: LedgerVerification
    closed: PeriodClose


def evidence_pack(source: EvidenceSource, generated_at: datetime) -> bytes:
    contents = dict(_contents(source))
    manifest = {
        "generado_en": generated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "periodo": source.period,
        "empresa": source.company_name,
        "cierre": source.closed.model_dump(mode="json"),
        "registro": source.verification.model_dump(mode="json"),
        "archivos": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in sorted({**contents, MANIFEST: _json(manifest)}.items()):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = UNIX_FILE
            info.external_attr = FILE_MODE
            archive.writestr(info, data, compresslevel=COMPRESSION_LEVEL)
    return buffer.getvalue()


def _contents(source: EvidenceSource) -> Iterator[tuple[str, bytes]]:
    yield "LEEME.txt", _readme(source).encode()
    yield "resumen.pdf", _summary_pdf(source)
    yield "conciliacion.csv", _reconciliation_csv(source)
    for invoice_id, acta in sorted(source.actas.items()):
        yield f"actas/{invoice_id}.json", _json(acta)
    yield "registro/registro.json", _json([json.loads(canonical_json(entry.model_dump())) for entry in source.ledger])
    yield "registro/verificacion.json", _json(source.verification.model_dump(mode="json"))
    yield "registro/verificar_registro.py", files("custodio.reconciliation").joinpath(VERIFIER).read_bytes()


def _json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _readme(source: EvidenceSource) -> str:
    return f"""Paquete de cierre de {_month(source.period)} · {source.company_name}

resumen.pdf             Lo pagado, retenido y rechazado en el mes, lo conciliado con el banco, las diferencias de
                        cambio, las comisiones y cada alerta con la nota de quien la revisó.
conciliacion.csv        Un movimiento del extracto por fila: cómo se emparejó, con qué factura y por qué.
actas/                  El acta de cada factura decidida en el mes: las 12 reglas, la razón y la ejecución del pago.
registro/registro.json  El registro encadenado completo (SHA-256), tal como lo guarda Custodio.
registro/verificacion.json
                        Lo que responde el verificador público de Custodio sobre ese registro.
registro/verificar_registro.py
                        El mismo algoritmo, sin dependencias: python3 verificar_registro.py registro.json
manifiesto.json         El SHA-256 de cada archivo y la fecha en que se generó este paquete (el único dato que
                        cambia si se vuelve a descargar).

El modelo leyó el extracto; el código emparejó y cerró; una persona revisó cada alerta.
"""


def _reconciliation_csv(source: EvidenceSource) -> bytes:
    movements = {movement.id: movement for movement in source.statement.movements}
    reviews = {review.movement_id: review for review in source.reviews}
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for result in source.outcome.movements:
        movement = movements[result.movement_id]
        review = reviews.get(result.movement_id)
        writer.writerow(
            [
                movement.row,
                movement.booked_on.isoformat() if movement.booked_on else "",
                movement.description,
                movement.reference or "",
                _plain(movement.amount),
                movement.currency or "",
                STATUS_LABELS[result.status],
                LEVEL_LABELS[result.level] if result.level else "",
                result.invoice_id or "",
                _plain(result.allocated) if result.invoice_id else "",
                _plain(result.difference),
                movements[result.duplicate_of].row if result.duplicate_of else "",
                result.reason,
                review.reviewer if review else "",
                review.note if review else "",
            ]
        )
    return ("﻿" + buffer.getvalue()).encode()  # the byte order mark makes spreadsheets read UTF-8


def _plain(value: Decimal | None) -> str:
    return "" if value is None else f"{value:.2f}"


def _month(period: str) -> str:
    year, month = period.split("-")
    return f"{month_name(date(int(year), int(month), 1))} de {year}"


class _Page:
    """A top-to-bottom writer that turns the page when it runs out of room."""

    def __init__(self, canvas: Canvas) -> None:
        self.canvas = canvas
        self.y = PAGE_HEIGHT - MARGIN

    def text(self, words: str, *, size: float = BODY_SIZE, bold: bool = False, color: tuple[float, ...] = INK) -> None:
        for line in simpleSplit(words, BOLD_FONT if bold else BODY_FONT, size, TEXT_WIDTH):
            self._room(size)
            self.canvas.setFont(BOLD_FONT if bold else BODY_FONT, size)
            self.canvas.setFillColorRGB(*color)
            self.canvas.drawString(MARGIN, self.y, line)
            self.y -= size * 1.45

    def figure(self, label: str, value: str) -> None:
        self._room(BODY_SIZE)
        self.canvas.setFont(BODY_FONT, BODY_SIZE)
        self.canvas.setFillColorRGB(*INK)
        self.canvas.drawString(MARGIN, self.y, label)
        self.canvas.setFont(BOLD_FONT, BODY_SIZE)
        self.canvas.drawRightString(FIGURES, self.y, value)
        self.y -= LINE

    def gap(self, size: float = LINE / 2) -> None:
        self.y -= size

    def _room(self, size: float) -> None:
        if self.y - size < MARGIN:
            self.canvas.showPage()
            self.y = PAGE_HEIGHT - MARGIN


def _summary_pdf(source: EvidenceSource) -> bytes:
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=letter, invariant=1)
    canvas.setTitle(f"Cierre de {_month(source.period)}")
    canvas.setAuthor("Custodio")
    page = _Page(canvas)
    _draw_title(page, source)
    _draw_decisions(page, source.summary)
    _draw_reconciliation(page, source)
    _draw_alerts(page, source)
    _draw_pending(page, source)
    _draw_ledger(page, source)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _draw_title(page: _Page, source: EvidenceSource) -> None:
    closed = source.closed
    page.text(f"Cierre de {_month(source.period)}", size=TITLE_SIZE, bold=True, color=BRAND)
    page.text(source.company_name, size=HEADING_SIZE)
    page.text(
        f"Cerrado el {day_month(closed.closed_at)} de {closed.closed_at.year} por {closed.closed_by}, en el asiento "
        f"#{closed.ledger_seq} del registro ({closed.ledger_hash[:16]}…). Cifras en {source.summary.currency}.",
        color=MUTED,
    )
    page.gap()


def _draw_decisions(page: _Page, summary: PeriodSummary) -> None:
    page.text("Decisiones del mes", size=HEADING_SIZE, bold=True)
    page.figure("Pagado (solo o con aprobación)", _tally(summary.paid, summary.currency, "factura", "facturas"))
    page.figure("Retenido", _tally(summary.held, summary.currency, "factura", "facturas"))
    page.figure("Rechazado", _tally(summary.rejected, summary.currency, "factura", "facturas"))
    page.figure("Esperan aprobación", _tally(summary.pending_approval, summary.currency, "factura", "facturas"))
    page.gap()


def _draw_reconciliation(page: _Page, source: EvidenceSource) -> None:
    summary, currency = source.summary, source.summary.currency
    page.text("Conciliación con el banco", size=HEADING_SIZE, bold=True)
    page.text(
        f"Extracto leído por {source.statement.reader}: "
        f"{counted(len(source.statement.movements), 'movimiento', 'movimientos')}. "
        f"Tolerancia de cambio {plus_minus_percent(source.outcome.settings.fx_tolerance_pct)}, ventana de "
        f"{counted(source.outcome.settings.date_window_days, 'día', 'días')}.",
        color=MUTED,
    )
    page.figure("Conciliado", _tally(summary.reconciled, currency, "movimiento", "movimientos"))
    page.figure("Diferencias de cambio", _tally(summary.differences, currency, "pago", "pagos"))
    page.figure("Comisiones bancarias", _tally(summary.fees, currency, "cargo", "cargos"))
    page.figure("Salidas sin factura y duplicados", _tally(summary.unexplained, currency, "movimiento", "movimientos"))
    page.figure("Ingresos (fuera de cuentas por pagar)", _tally(summary.inflows, currency, "movimiento", "movimientos"))
    page.figure("Pagos que aún no aparecen", _tally(summary.pending_in_bank, currency, "pago", "pagos"))
    page.gap()


def _draw_alerts(page: _Page, source: EvidenceSource) -> None:
    movements = {movement.id: movement for movement in source.statement.movements}
    reviews = {review.movement_id: review for review in source.reviews}
    alerts = [item for item in source.outcome.movements if item.status in NEEDS_REVIEW]
    page.text("Alertas revisadas", size=HEADING_SIZE, bold=True)
    if not alerts:
        page.text("Ningún movimiento necesitó revisión.", color=MUTED)
    for item in alerts:
        movement = movements[item.movement_id]
        amount = money(abs(movement.amount), movement.currency or "") if movement.amount is not None else "NO LEÍDO"
        page.text(f"Fila {movement.row} · {movement.description} · {amount} · {STATUS_LABELS[item.status]}", bold=True)
        page.text(item.reason, size=SMALL_SIZE, color=MUTED)
        review = reviews.get(item.movement_id)
        if review:
            page.text(f"Revisó {review.reviewer} (asiento #{review.ledger_seq}): {review.note}")
        page.gap(4)
    page.gap()


def _draw_pending(page: _Page, source: EvidenceSource) -> None:
    pending = [payment for payment in source.outcome.payments if payment.status is PaymentStatus.PENDING]
    if not pending:
        return
    page.text("Pagos que aún no aparecen en el banco", size=HEADING_SIZE, bold=True)
    for payment in pending:
        page.text(f"{payment.invoice_id} · {payment.supplier_name or ''} · {payment.reason}")
    page.gap()


def _draw_ledger(page: _Page, source: EvidenceSource) -> None:
    verification = source.verification
    state = "íntegra" if verification.valid else f"rota en el asiento #{verification.first_broken_seq}"
    page.text("Registro encadenado", size=HEADING_SIZE, bold=True)
    page.text(
        f"{counted(verification.length, 'asiento', 'asientos')}, cadena {state}. Último hash confiable: "
        f"{verification.head_hash or 'ninguno'}. Se verifica con registro/verificar_registro.py.",
        size=SMALL_SIZE,
    )


def _tally(tally: Tally, currency: str, singular: str, plural: str) -> str:
    return f"{counted(tally.count, singular, plural)} · {money(tally.total, currency)}"
