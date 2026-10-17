"""Reading invoices: documents in, `ExtractedInvoice` out. Owned by lane L2.

The model reads; code verifies. Every extracted value carries the exact quote that supports it, and
`ExtractedField.verified` is set by code only after finding that quote in the source text. Hidden text is
detected by code (character colors, sizes and positions), never by asking a model whether text is hidden.

Pipelines, named in `ExtractedInvoice.reader`:
- PDF with text: pdfplumber (visible text + hidden findings) -> Claude.
- PDF without text (a scan): pdfplumber rasterizes each page -> vision transcription -> Claude.
- Image: vision transcription -> Claude.
- Plain text: Claude.
Without ANTHROPIC_API_KEY, plain text and PDFs with text are read from labelled lines by code (`labels`) and the
pipelines that need vision raise `llm.LLMNotConfigured`.
Scanned pages go to the model as images, never as a PDF document block: a document block would also carry the
PDF's text layer, which is where hidden text lives.
Every pipeline also scans the visible text for instructions addressed to the agent.

Failures are typed: UnsupportedDocument, UnreadableDocument, MalformedReading
(custodio.extraction.errors) and custodio.llm.LLMError. Callers escalate or say "NO MEDIDO"; nothing is guessed.
"""

from __future__ import annotations

import io
import mimetypes
from typing import Literal

from PIL import Image, UnidentifiedImageError

from custodio.config import get_settings
from custodio.contracts import ExtractedField, ExtractedInvoice, HiddenTextFinding, InvoiceSource
from custodio.engine.domains import first_email
from custodio.extraction import labels, pdf, structure, vision
from custodio.extraction.errors import UnreadableDocument, UnsupportedDocument
from custodio.extraction.instructions import find_instructions
from custodio.extraction.render import render_invoice
from custodio.extraction.source import SourceText

__all__ = ["extract_document", "extract_text", "labels", "render_invoice"]

SupportedMediaType = Literal["application/pdf", "image/png", "image/jpeg", "image/webp"]
SUPPORTED_MEDIA_TYPES: tuple[SupportedMediaType, ...] = ("application/pdf", "image/png", "image/jpeg", "image/webp")
GENERIC_MEDIA_TYPES = frozenset({"", "application/octet-stream"})
# R1 fields: if any of them is not verified, the whole reading is not trustworthy.
CRITICAL_FIELDS = ("supplier_name", "amount", "currency", "account_number")


def extract_document(data: bytes, *, filename: str, media_type: str, document_id: str) -> ExtractedInvoice:
    """Read a PDF or an image (png, jpeg, webp) into an ExtractedInvoice."""
    kind = _media_type(media_type, filename)
    if kind == "application/pdf":
        return _extract_pdf(data, document_id)
    return _extract_image(data, kind, document_id)


def extract_text(text: str, *, document_id: str, source: InvoiceSource = InvoiceSource.TEXT) -> ExtractedInvoice:
    """Read a plain-text invoice (email body, WhatsApp message, payment intent text)."""
    return _read(SourceText(pages=(text,)), document_id=document_id, origin=source, readers=("text",), hidden=[])


def _media_type(declared: str, filename: str) -> SupportedMediaType:
    media_type = declared.split(";")[0].strip().lower()
    if media_type in GENERIC_MEDIA_TYPES:
        media_type = mimetypes.guess_type(filename)[0] or ""
    for supported in SUPPORTED_MEDIA_TYPES:
        if media_type == supported:
            return supported
    raise UnsupportedDocument(f"Custodio lee PDF, PNG, JPEG o WebP; «{filename}» llegó como «{declared}».")


def _extract_pdf(data: bytes, document_id: str) -> ExtractedInvoice:
    reading = pdf.read_pdf(data)
    readers: tuple[str, ...]
    if reading.has_visible_text:
        source, readers = SourceText(pages=reading.pages), ("pdfplumber",)
    else:
        transcripts = [vision.transcribe(page, "image/png") for page in pdf.rasterize(data)]
        if not transcripts:
            raise UnreadableDocument("El PDF no tiene páginas.")
        source = SourceText(pages=tuple(transcript.text for transcript in transcripts))
        readers = ("pdfplumber", f"vision:{transcripts[0].model}")
    return _read(source, document_id=document_id, origin=InvoiceSource.PDF, readers=readers, hidden=reading.findings)


def _extract_image(data: bytes, media_type: vision.ImageMediaType, document_id: str) -> ExtractedInvoice:
    _ensure_image(data)
    transcript = vision.transcribe(data, media_type)
    return _read(
        SourceText(pages=(transcript.text,)),
        document_id=document_id,
        origin=InvoiceSource.IMAGE,
        readers=(f"vision:{transcript.model}",),
        hidden=[],
    )


def _ensure_image(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise UnreadableDocument("El archivo dice ser una imagen pero no se puede abrir.") from error


def _read(
    source: SourceText,
    *,
    document_id: str,
    origin: InvoiceSource,
    readers: tuple[str, ...],
    hidden: list[HiddenTextFinding],
) -> ExtractedInvoice:
    reading = structure.read_fields(source) if get_settings().anthropic_configured else labels.read_fields(source)
    return ExtractedInvoice.model_validate(
        {
            "document_id": document_id,
            "source": origin,
            **reading.fields,
            "visible_text": source.text,
            "sender_email": first_email(source.text),
            "hidden_findings": [*hidden, *find_instructions(source)],
            "reader": "+".join((*readers, reading.model)),
            "overall_confidence": _overall_confidence(reading.fields),
        }
    )


def _overall_confidence(fields: dict[str, ExtractedField]) -> float:
    """The weakest critical field decides; an unverified one counts as zero."""
    return min(fields[name].confidence if fields[name].verified else 0.0 for name in CRITICAL_FIELDS)
