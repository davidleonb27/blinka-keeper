"""Invoices as PDF, with hidden text drawn by one of the techniques attackers use."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable
from enum import StrEnum

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen.canvas import Canvas

from custodio.extraction.content import TITLE, InvoiceContent

PAGE_WIDTH, PAGE_HEIGHT = float(letter[0]), float(letter[1])
MARGIN = 48.0
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
RIGHT = PAGE_WIDTH - MARGIN
HEADER_HEIGHT = 110.0
BODY_FONT, BOLD_FONT = "Helvetica", "Helvetica-Bold"
BODY_SIZE = 10.0
SMALL_SIZE = 7.5
LINE = 14.0
TINY_SIZE = 1.0
LEADING = 1.4  # line height as a multiple of the font size
DESCENT = 0.3  # how far glyphs reach below the baseline, as a multiple of the font size
INK = (0.13, 0.14, 0.17)
MUTED = (0.42, 0.44, 0.48)
TABLE_FILL = (0.93, 0.94, 0.96)
BRAND_COLORS = ((0.07, 0.24, 0.42), (0.10, 0.36, 0.30), (0.36, 0.13, 0.30), (0.20, 0.20, 0.24), (0.55, 0.22, 0.10))
DESCRIPTION_WIDTH = 270.0
COLUMN_QUANTITY, COLUMN_UNIT, COLUMN_TOTAL = 340.0, 450.0, RIGHT - 8
FOOTER = (
    "Representación gráfica de la factura electrónica de venta. Documento generado por el sistema de "
    "facturación del proveedor."
)
STAMP_TEXT = "RECIBIDO - CONTABILIDAD"
STAMP_PADDING = 6.0
STAMP_PIXELS_PER_POINT = 3


class HiddenTechnique(StrEnum):
    WHITE_TEXT = "white_text"  # white on the white page
    TINY_FONT = "tiny_font"  # 1 pt, in ink color
    OFF_PAGE = "off_page"  # drawn to the right of the page box
    UNDER_SHAPE = "under_shape"  # covered by an opaque white rectangle drawn after it
    UNDER_IMAGE = "under_image"  # covered by a "received" stamp image drawn after it
    METADATA = "metadata"  # the PDF Subject field
    ANNOTATION = "annotation"  # a text annotation's contents


PDF_TECHNIQUES: tuple[HiddenTechnique, ...] = tuple(HiddenTechnique)


def render_pdf(content: InvoiceContent, technique: HiddenTechnique) -> bytes:
    buffer = io.BytesIO()
    page = Canvas(buffer, pagesize=letter, invariant=1)
    _set_metadata(page, content)
    y = _draw_header(page, content)
    y = _draw_dates(page, content, y)
    y = _draw_items(page, content, y)
    y = _draw_totals(page, content, y)
    y = _draw_payment(page, content, y)
    y = _draw_note(page, content, y)
    if content.hidden_text:
        _HIDE[technique](page, content.hidden_text, y)
    _draw_footer(page)
    page.showPage()
    page.save()
    return buffer.getvalue()


def _set_metadata(page: Canvas, content: InvoiceContent) -> None:
    page.setTitle(f"Factura {content.number}")
    page.setAuthor(content.supplier)
    page.setCreator("Sistema de facturación electrónica")


def _brand_color(supplier: str) -> tuple[float, float, float]:
    digest = hashlib.sha256(supplier.encode()).digest()
    return BRAND_COLORS[digest[0] % len(BRAND_COLORS)]


def _draw_header(page: Canvas, content: InvoiceContent) -> float:
    top = PAGE_HEIGHT - HEADER_HEIGHT
    page.setFillColorRGB(*_brand_color(content.supplier))
    page.rect(0, top, PAGE_WIDTH, HEADER_HEIGHT, fill=1, stroke=0)
    page.setFillColorRGB(1, 1, 1)
    page.setFont(BOLD_FONT, 18)
    page.drawString(MARGIN, PAGE_HEIGHT - 52, content.supplier)
    page.setFont(BODY_FONT, BODY_SIZE)
    page.drawString(MARGIN, PAGE_HEIGHT - 70, content.tax_line)
    page.setFont(BOLD_FONT, 11)
    page.drawRightString(RIGHT, PAGE_HEIGHT - 52, TITLE)
    page.setFont(BODY_FONT, 12)
    page.drawRightString(RIGHT, PAGE_HEIGHT - 70, f"No. {content.number}")
    return top - 36


def _draw_dates(page: Canvas, content: InvoiceContent, y: float) -> float:
    page.setFillColorRGB(*INK)
    page.setFont(BODY_FONT, BODY_SIZE)
    for line in filter(None, (content.issue_line, content.due_line)):
        page.drawString(MARGIN, y, line)
        y -= LINE
    return y - 20


def _draw_items(page: Canvas, content: InvoiceContent, y: float) -> float:
    page.setFillColorRGB(*TABLE_FILL)
    page.rect(MARGIN, y - 6, CONTENT_WIDTH, 20, fill=1, stroke=0)
    page.setFillColorRGB(*INK)
    page.setFont(BOLD_FONT, 9)
    page.drawString(MARGIN + 8, y, "Descripción")
    page.drawString(COLUMN_QUANTITY, y, "Cant.")
    page.drawRightString(COLUMN_UNIT, y, "Valor unitario")
    page.drawRightString(COLUMN_TOTAL, y, "Valor total")
    y -= 24
    page.setFont(BODY_FONT, BODY_SIZE)
    page.drawString(COLUMN_QUANTITY, y, "1")
    page.drawRightString(COLUMN_UNIT, y, content.amount_text)
    page.drawRightString(COLUMN_TOTAL, y, content.amount_text)
    for line in simpleSplit(content.description, BODY_FONT, BODY_SIZE, DESCRIPTION_WIDTH):
        page.drawString(MARGIN + 8, y, line)
        y -= LINE
    page.setStrokeColorRGB(*TABLE_FILL)
    page.line(MARGIN, y + 4, RIGHT, y + 4)
    return y - 16


def _draw_totals(page: Canvas, content: InvoiceContent, y: float) -> float:
    page.setFont(BODY_FONT, BODY_SIZE)
    page.drawString(COLUMN_QUANTITY, y, "Subtotal")
    page.drawRightString(COLUMN_TOTAL, y, content.amount_text)
    y -= LINE + 4
    page.setFont(BOLD_FONT, 12)
    page.drawString(COLUMN_QUANTITY, y, "TOTAL A PAGAR")
    page.drawRightString(COLUMN_TOTAL, y, content.amount_text)
    return y - 40


def _draw_payment(page: Canvas, content: InvoiceContent, y: float) -> float:
    page.setFont(BOLD_FONT, BODY_SIZE)
    page.drawString(MARGIN, y, "Datos para el pago")
    page.setFont(BODY_FONT, BODY_SIZE)
    for line in content.bank_lines:
        y -= LINE
        page.drawString(MARGIN, y, line)
    return y - 30


def _draw_note(page: Canvas, content: InvoiceContent, y: float) -> float:
    if not content.note:
        return y
    page.setFont(BODY_FONT, BODY_SIZE)
    for line in simpleSplit(content.note, BODY_FONT, BODY_SIZE, CONTENT_WIDTH):
        page.drawString(MARGIN, y, line)
        y -= LINE
    return y - 16


def _draw_footer(page: Canvas) -> None:
    page.setFillColorRGB(*MUTED)
    page.setFont(BODY_FONT, SMALL_SIZE)
    page.drawString(MARGIN, 36, FOOTER)


def _draw_lines(page: Canvas, text: str, x: float, y: float, size: float = BODY_SIZE) -> tuple[float, float]:
    """Draw `text` wrapped to the content width from baseline `y`; return the block's bottom and height."""
    page.setFont(BODY_FONT, size)
    lines = simpleSplit(text, BODY_FONT, size, CONTENT_WIDTH)
    for number, line in enumerate(lines):
        page.drawString(x, y - number * size * LEADING, line)
    bottom = y - (len(lines) - 1) * size * LEADING - size * DESCENT
    return bottom, y + size - bottom


def _hide_white(page: Canvas, text: str, y: float) -> None:
    page.setFillColorRGB(1, 1, 1)
    _draw_lines(page, text, MARGIN, y)


def _hide_tiny(page: Canvas, text: str, y: float) -> None:
    page.setFillColorRGB(*INK)
    _draw_lines(page, text, MARGIN, y, size=TINY_SIZE)


def _hide_off_page(page: Canvas, text: str, y: float) -> None:
    page.setFillColorRGB(*INK)
    _draw_lines(page, text, PAGE_WIDTH + MARGIN, y)


def _hide_under_shape(page: Canvas, text: str, y: float) -> None:
    page.setFillColorRGB(*INK)
    bottom, height = _draw_lines(page, text, MARGIN, y)
    page.setFillColorRGB(1, 1, 1)
    page.rect(
        MARGIN - STAMP_PADDING,
        bottom - STAMP_PADDING,
        CONTENT_WIDTH + 2 * STAMP_PADDING,
        height + 2 * STAMP_PADDING,
        fill=1,
        stroke=0,
    )


def _hide_under_image(page: Canvas, text: str, y: float) -> None:
    page.setFillColorRGB(*INK)
    bottom, height = _draw_lines(page, text, MARGIN, y)
    width, stamp_height = CONTENT_WIDTH + 2 * STAMP_PADDING, height + 2 * STAMP_PADDING
    page.drawImage(
        ImageReader(_stamp(width, stamp_height)),
        MARGIN - STAMP_PADDING,
        bottom - STAMP_PADDING,
        width=width,
        height=stamp_height,
    )


def _hide_in_metadata(page: Canvas, text: str, y: float) -> None:
    page.setSubject(text)


def _hide_in_annotation(page: Canvas, text: str, y: float) -> None:
    page.textAnnotation(text, Rect=(RIGHT - 16, y - 16, RIGHT, y))


def _stamp(width: float, height: float) -> Image.Image:
    """An opaque "received" stamp, the kind accounting teams put on paper invoices."""
    size = (int(width * STAMP_PIXELS_PER_POINT), int(height * STAMP_PIXELS_PER_POINT))
    stamp = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(stamp)
    draw.rounded_rectangle((4, 4, size[0] - 5, size[1] - 5), radius=18, outline=(176, 32, 40), width=6)
    font = ImageFont.load_default(size=max(18, size[1] // 3))
    draw.text((size[0] / 2, size[1] / 2), STAMP_TEXT, fill=(176, 32, 40), font=font, anchor="mm")
    return stamp


_HIDE: dict[HiddenTechnique, Callable[[Canvas, str, float], None]] = {
    HiddenTechnique.WHITE_TEXT: _hide_white,
    HiddenTechnique.TINY_FONT: _hide_tiny,
    HiddenTechnique.OFF_PAGE: _hide_off_page,
    HiddenTechnique.UNDER_SHAPE: _hide_under_shape,
    HiddenTechnique.UNDER_IMAGE: _hide_under_image,
    HiddenTechnique.METADATA: _hide_in_metadata,
    HiddenTechnique.ANNOTATION: _hide_in_annotation,
}
