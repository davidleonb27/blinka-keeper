"""What a person can see in a PDF, and what is there but hidden from them.

Every character is judged by code from its color, size and position, in drawing order (pdfplumber/pdfminer keep
the content-stream order): a later opaque shape or image over a character covers it; the last opaque shape under
it is its background. Hidden characters never reach `pages`, so the model that structures the invoice never reads
them; they become HiddenTextFinding records for R2 instead.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from pdfplumber.utils.exceptions import PdfminerException
from pdfplumber.utils.text import extract_text
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from custodio.contracts import HiddenTextFinding, HiddenTextKind
from custodio.extraction.errors import UnreadableDocument, UnsupportedDocument
from custodio.extraction.instructions import speaks_to_agent
from custodio.extraction.text import fold

PdfObject = dict[str, Any]
Rgb = tuple[float, float, float]
Box = tuple[float, float, float, float]  # x0, top, x1, bottom; pdfplumber page coordinates

PAGE_BACKGROUND: Rgb = (1.0, 1.0, 1.0)
INVISIBLE_COLOR_DELTA = 0.08  # max per-channel distance (0..1) at which text and background look the same
MIN_LEGIBLE_SIZE_PT = 2.0
MAX_RASTER_PAGES = 5
RASTER_DPI = 200
# Fields the PDF writer fills on its own; only text addressed to the agent counts as hidden there.
TOOL_FIELDS = frozenset({"Creator", "Producer", "CreationDate", "ModDate", "Trapped"})
# Other fields (Title, Subject, Keywords, custom keys) hide text when they carry this many words the page never shows.
METADATA_UNSEEN_WORDS = 4

# When a character qualifies for several kinds, the most deliberate one is reported.
_KIND_ORDER = (
    HiddenTextKind.OFF_PAGE,
    HiddenTextKind.COVERED,
    HiddenTextKind.INVISIBLE_COLOR,
    HiddenTextKind.TINY_FONT,
)


@dataclass(frozen=True)
class PdfReading:
    pages: tuple[str, ...]  # visible text, one entry per page
    findings: list[HiddenTextFinding]

    @property
    def has_visible_text(self) -> bool:
        return any(page.strip() for page in self.pages)


@dataclass(frozen=True)
class _Layer:
    order: int
    box: Box
    color: Rgb | None  # None for images: their color under a character is unknown

    def holds(self, point: tuple[float, float]) -> bool:
        return _inside(point, self.box)


@dataclass(frozen=True)
class _PageReading:
    text: str
    findings: list[HiddenTextFinding]


def read_pdf(data: bytes) -> PdfReading:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            readings = [_read_page(page) for page in pdf.pages]
        pages = tuple(reading.text for reading in readings)
        document = PdfReader(io.BytesIO(data))
        unseen = [*_metadata_findings(document, _words(" ".join(pages))), *_annotation_findings(document)]
    except (PDFSyntaxError, PdfminerException, PyPdfError) as error:
        raise UnreadableDocument("El archivo dice ser un PDF pero no se puede leer.") from error
    return PdfReading(pages=pages, findings=[finding for reading in readings for finding in reading.findings] + unseen)


def rasterize(data: bytes) -> list[bytes]:
    """Each page as a PNG, for the vision transcription of PDFs that carry no text (scans)."""
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > MAX_RASTER_PAGES:
                raise UnsupportedDocument(f"Un PDF escaneado de más de {MAX_RASTER_PAGES} páginas no es una factura.")
            return [_png(page.to_image(resolution=RASTER_DPI).original) for page in pdf.pages]
    except (PDFSyntaxError, PdfminerException) as error:
        raise UnreadableDocument("El archivo dice ser un PDF pero no se puede dibujar.") from error


def _read_page(page: Any) -> _PageReading:
    objects: list[PdfObject] = [
        obj for obj in page.iter_layout_objects(list(page.layout)) if obj["object_type"] != "anno"
    ]
    layers = [layer for order, obj in enumerate(objects) if (layer := _layer(order, obj)) is not None]
    page_box: Box = tuple(page.bbox)
    judged = [
        (obj, _hidden_kind(order, obj, page_box, layers))
        for order, obj in enumerate(objects)
        if obj["object_type"] == "char"
    ]
    visible = [obj for obj, kind in judged if kind is None]
    number: int = page.page_number
    findings = [
        _char_finding(kind, text, number)
        for kind in _KIND_ORDER
        if (text := _text([obj for obj, judged_kind in judged if judged_kind is kind]))
    ]
    return _PageReading(text=_text(visible), findings=findings)


def _layer(order: int, obj: PdfObject) -> _Layer | None:
    box: Box = (obj["x0"], obj["top"], obj["x1"], obj["bottom"])
    if obj["object_type"] == "image":
        return _Layer(order, box, None)
    if obj["object_type"] in {"rect", "curve"} and obj.get("fill"):
        return _Layer(order, box, _rgb(obj.get("non_stroking_color")))
    return None


def _hidden_kind(order: int, char: PdfObject, page_box: Box, layers: list[_Layer]) -> HiddenTextKind | None:
    center = ((char["x0"] + char["x1"]) / 2, (char["top"] + char["bottom"]) / 2)
    if not _inside(center, page_box):
        return HiddenTextKind.OFF_PAGE
    if any(layer.order > order and layer.holds(center) for layer in layers):
        return HiddenTextKind.COVERED
    if _same_color(_rgb(char.get("non_stroking_color")), _background(order, center, layers)):
        return HiddenTextKind.INVISIBLE_COLOR
    if char["size"] < MIN_LEGIBLE_SIZE_PT:
        return HiddenTextKind.TINY_FONT
    return None


def _background(order: int, point: tuple[float, float], layers: list[_Layer]) -> Rgb | None:
    under = [layer for layer in layers if layer.order < order and layer.holds(point)]
    return under[-1].color if under else PAGE_BACKGROUND


def _same_color(text: Rgb | None, background: Rgb | None) -> bool:
    if text is None or background is None:
        return False
    return all(abs(a - b) <= INVISIBLE_COLOR_DELTA for a, b in zip(text, background, strict=True))


def _rgb(color: Any) -> Rgb | None:
    """pdfminer colors are gray, RGB or CMYK tuples in 0..1; patterns and unknown spaces return None."""
    if not isinstance(color, tuple) or not all(isinstance(value, int | float) for value in color):
        return None
    if len(color) == 1:
        return (color[0], color[0], color[0])
    if len(color) == 3:
        return (color[0], color[1], color[2])
    if len(color) == 4:
        cyan, magenta, yellow, black = color
        return ((1 - cyan) * (1 - black), (1 - magenta) * (1 - black), (1 - yellow) * (1 - black))
    return None


def _inside(point: tuple[float, float], box: Box) -> bool:
    x, y = point
    x0, top, x1, bottom = box
    return x0 <= x <= x1 and top <= y <= bottom


def _text(chars: list[PdfObject]) -> str:
    return str(extract_text(chars)).strip() if chars else ""


_CHAR_DETAIL = {
    HiddenTextKind.OFF_PAGE: "Texto fuera del área visible de la página {page}.",
    HiddenTextKind.COVERED: "Texto tapado por una figura o una imagen en la página {page}.",
    HiddenTextKind.INVISIBLE_COLOR: "Texto del mismo color que el fondo en la página {page}.",
    HiddenTextKind.TINY_FONT: f"Texto en letra de menos de {MIN_LEGIBLE_SIZE_PT:g} pt en la página {{page}}.",
}
_UNSEEN = " Una persona no lo ve, pero un lector automático sí lo lee."


def _char_finding(kind: HiddenTextKind, text: str, page: int) -> HiddenTextFinding:
    return HiddenTextFinding(kind=kind, text=text, page=page, detail=_CHAR_DETAIL[kind].format(page=page) + _UNSEEN)


def _annotation_findings(document: PdfReader) -> Iterator[HiddenTextFinding]:
    """Annotation contents (sticky notes, comments): they do not print and a reader rarely opens them."""
    for page, annotation in _annotations(document):
        contents = str(annotation.get("/Contents") or "").strip()
        if contents:
            yield HiddenTextFinding(
                kind=HiddenTextKind.METADATA,
                text=contents,
                page=page,
                detail=f"Texto en una anotación de la página {page}, que no se ve al imprimir la factura.",
            )


def _annotations(document: PdfReader) -> Iterator[tuple[int, Any]]:
    for page, content in enumerate(document.pages, start=1):
        annotations = content.get("/Annots")
        for reference in annotations.get_object() if annotations is not None else ():
            yield page, reference.get_object()


def _metadata_findings(document: PdfReader, visible_words: set[str]) -> Iterator[HiddenTextFinding]:
    for key, value in (document.metadata or {}).items():
        field, text = str(key).lstrip("/"), str(value).strip()
        if text and _hides_text(field, text, visible_words):
            yield HiddenTextFinding(
                kind=HiddenTextKind.METADATA,
                text=text,
                detail=f"Texto escondido en los metadatos del PDF (campo {field}).{_UNSEEN}",
            )


def _hides_text(field: str, text: str, visible_words: set[str]) -> bool:
    if speaks_to_agent(text):
        return True
    if field in TOOL_FIELDS:
        return False
    return len(_words(text) - visible_words) >= METADATA_UNSEEN_WORDS


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", fold(text)))


def _png(image: Any) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
