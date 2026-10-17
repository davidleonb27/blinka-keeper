"""Invoices as images: a phone photo of a paper invoice, or a WhatsApp chat screenshot.

Hidden text in an image is drawn in a color one shade off its background: a person does not see it, an OCR model
may still read it. Code cannot tell it apart from pixels, so on images only the instruction patterns (R2) catch it.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import reportlab
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from custodio.extraction.content import GREETING, TITLE, InvoiceContent

Color = tuple[int, int, int]
Font = ImageFont.FreeTypeFont

# Bitstream Vera ships with reportlab and covers Spanish accents; Pillow's built-in font does not.
_FONTS = Path(reportlab.__file__).parent / "fonts"

INK: Color = (34, 36, 43)
MUTED: Color = (110, 114, 122)
FAINT_DELTA = 4  # how far hidden text is from its background, per channel (out of 255)

PHOTO_SIZE = (1100, 1400)
PAPER_SIZE = (900, 1180)
PAPER: Color = (251, 250, 246)
TABLE: Color = (236, 237, 240)
TABLETOP: Color = (92, 80, 68)
PHOTO_TILT_DEGREES = 1.4
PHOTO_BLUR_RADIUS = 0.7
PAPER_MARGIN = 56

CHAT_WIDTH, CHAT_MIN_HEIGHT = 720, 1280
CHAT_TOP_BAR: Color = (7, 94, 84)
CHAT_WALLPAPER: Color = (236, 229, 221)
BUBBLE: Color = (255, 255, 255)
BUBBLE_MAX_WIDTH = 540
BUBBLE_PADDING = 18
BUBBLE_GAP = 22
CHAT_TIME = "9:41"
LINE_GAP = 10


def render_photo(content: InvoiceContent) -> bytes:
    paper = Image.new("RGB", PAPER_SIZE, PAPER)
    _draw_paper(ImageDraw.Draw(paper), content)
    tilted = paper.convert("RGBA").rotate(PHOTO_TILT_DEGREES, resample=Image.Resampling.BICUBIC, expand=True)
    photo = Image.new("RGB", PHOTO_SIZE, TABLETOP)
    offset = ((PHOTO_SIZE[0] - tilted.width) // 2, (PHOTO_SIZE[1] - tilted.height) // 2)
    photo.paste(tilted, offset, tilted)
    return _png(_light_from_the_left(photo).filter(ImageFilter.GaussianBlur(PHOTO_BLUR_RADIUS)))


def render_chat(content: InvoiceContent) -> bytes:
    font, small = _font(24), _font(16)
    bubbles = [_wrap_paragraphs(text, font, BUBBLE_MAX_WIDTH - 2 * BUBBLE_PADDING) for text in _messages(content)]
    line_height = int(font.size) + LINE_GAP
    heights = [len(lines) * line_height + 2 * BUBBLE_PADDING + int(small.size) for lines in bubbles]
    height = max(CHAT_MIN_HEIGHT, 230 + sum(heights) + BUBBLE_GAP * len(heights) + 120)
    chat = Image.new("RGB", (CHAT_WIDTH, height), CHAT_WALLPAPER)
    draw = ImageDraw.Draw(chat)
    _draw_chat_header(draw, content)
    y = 200
    for lines, bubble_height in zip(bubbles, heights, strict=True):
        _draw_bubble(draw, lines, y, bubble_height, font, small)
        y += bubble_height + BUBBLE_GAP
    if content.hidden_text:
        _draw_faint(draw, content.hidden_text, (40, y), BUBBLE_MAX_WIDTH, CHAT_WALLPAPER)
    _draw_input_bar(draw, height)
    return _png(chat)


def _messages(content: InvoiceContent) -> list[str]:
    invoice = "\n".join(
        filter(
            None,
            (
                f"Factura {content.number}",
                content.issue_line,
                content.due_line,
                f"Concepto: {content.description}",
                f"Total a pagar: {content.amount_text}",
            ),
        )
    )
    payment = "\n".join(("Datos para el pago:", *content.bank_lines, content.tax_line))
    return [content.note or GREETING, invoice, payment]


def _draw_paper(draw: ImageDraw.ImageDraw, content: InvoiceContent) -> None:
    width = PAPER_SIZE[0]
    left, right = PAPER_MARGIN, width - PAPER_MARGIN
    draw.rectangle((0, 0, width, 150), fill=(18, 61, 107))
    draw.text((left, 46), content.supplier, fill="white", font=_font(34, bold=True))
    draw.text((left, 96), content.tax_line, fill="white", font=_font(20))
    draw.text((right, 50), TITLE, fill="white", font=_font(18), anchor="ra")
    draw.text((right, 96), f"No. {content.number}", fill="white", font=_font(22), anchor="ra")
    body, bold = _font(20), _font(22, bold=True)
    y = 200
    for line in filter(None, (content.issue_line, content.due_line)):
        draw.text((left, y), line, fill=INK, font=body)
        y += 32
    y += 30
    draw.rectangle((left, y, right, y + 40), fill=TABLE)
    draw.text((left + 12, y + 10), "Descripción", fill=INK, font=body)
    draw.text((right - 12, y + 10), "Valor total", fill=INK, font=body, anchor="ra")
    y += 56
    draw.text((right - 12, y), content.amount_text, fill=INK, font=body, anchor="ra")
    for line in _wrap(content.description, body, 480):
        draw.text((left + 12, y), line, fill=INK, font=body)
        y += 30
    y += 30
    total_left = right - 12 - draw.textlength(content.amount_text, font=bold)
    draw.text((total_left - 24, y), "TOTAL A PAGAR", fill=INK, font=bold, anchor="ra")
    draw.text((right - 12, y), content.amount_text, fill=INK, font=bold, anchor="ra")
    y += 80
    draw.text((left, y), "Datos para el pago", fill=INK, font=bold)
    for line in content.bank_lines:
        y += 32
        draw.text((left, y), line, fill=INK, font=body)
    y += 60
    for line in _wrap_paragraphs(content.note or "", body, right - left):
        draw.text((left, y), line, fill=INK, font=body)
        y += 30
    if content.hidden_text:
        _draw_faint(draw, content.hidden_text, (left, y + 20), right - left, PAPER)
    draw.text(
        (left, PAPER_SIZE[1] - 60), "Representación gráfica de la factura electrónica.", fill=MUTED, font=_font(16)
    )


def _draw_chat_header(draw: ImageDraw.ImageDraw, content: InvoiceContent) -> None:
    draw.rectangle((0, 0, CHAT_WIDTH, 120), fill=CHAT_TOP_BAR)
    draw.text((24, 60), "<", fill="white", font=_font(34), anchor="lm")
    draw.ellipse((64, 32, 120, 88), fill=(204, 214, 221))
    draw.text((92, 60), content.supplier[:1].upper(), fill=CHAT_TOP_BAR, font=_font(28), anchor="mm")
    draw.text((138, 40), content.supplier, fill="white", font=_font(26))
    draw.text((138, 74), "en línea", fill=(207, 233, 227), font=_font(18))
    draw.rounded_rectangle((CHAT_WIDTH // 2 - 60, 140, CHAT_WIDTH // 2 + 60, 176), radius=10, fill=(225, 243, 251))
    draw.text((CHAT_WIDTH // 2, 158), "HOY", fill=MUTED, font=_font(18), anchor="mm")


def _draw_bubble(draw: ImageDraw.ImageDraw, lines: list[str], top: int, height: int, font: Font, small: Font) -> None:
    widths = [draw.textlength(line, font=font) for line in lines]
    width = int(max(widths, default=0)) + 2 * BUBBLE_PADDING + 60
    left = 24
    draw.rounded_rectangle((left, top, left + width, top + height), radius=16, fill=BUBBLE)
    y = top + BUBBLE_PADDING
    for line in lines:
        draw.text((left + BUBBLE_PADDING, y), line, fill=INK, font=font)
        y += int(font.size) + LINE_GAP
    draw.text((left + width - BUBBLE_PADDING, top + height - 10), CHAT_TIME, fill=MUTED, font=small, anchor="rb")


def _draw_input_bar(draw: ImageDraw.ImageDraw, height: int) -> None:
    draw.rounded_rectangle((16, height - 86, CHAT_WIDTH - 100, height - 22), radius=32, fill=BUBBLE)
    draw.text((48, height - 54), "Mensaje", fill=MUTED, font=_font(22), anchor="lm")
    draw.ellipse((CHAT_WIDTH - 86, height - 86, CHAT_WIDTH - 22, height - 22), fill=(0, 168, 132))


def _draw_faint(draw: ImageDraw.ImageDraw, text: str, origin: tuple[int, int], width: int, background: Color) -> None:
    font = _font(14)
    faint = tuple(max(0, channel - FAINT_DELTA) for channel in background)
    x, y = origin
    for line in _wrap(text, font, width):
        draw.text((x, y), line, fill=faint, font=font)
        y += 18


def _light_from_the_left(photo: Image.Image) -> Image.Image:
    """Darken the right side slightly, like a photo taken next to a window."""
    gradient = Image.linear_gradient("L").rotate(90).resize(photo.size)
    shade = Image.new("RGB", photo.size, (0, 0, 0))
    return Image.composite(photo, shade, gradient.point(lambda value: 255 - value // 6))


def _wrap_paragraphs(text: str, font: Font, width: int) -> list[str]:
    return [line for paragraph in text.splitlines() for line in _wrap(paragraph, font, width)]


def _wrap(text: str, font: Font, width: int) -> list[str]:
    return list(_wrapped(text.split(), font, width))


def _wrapped(words: list[str], font: Font, width: int) -> Iterator[str]:
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and font.getlength(candidate) > width:
            yield line
            candidate = word
        line = candidate
    if line:
        yield line


@lru_cache
def _font(size: int, *, bold: bool = False) -> Font:
    return ImageFont.truetype(str(_FONTS / ("VeraBd.ttf" if bold else "Vera.ttf")), size)


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
