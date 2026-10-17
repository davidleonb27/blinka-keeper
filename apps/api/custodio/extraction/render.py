"""`render_invoice`: one InvoiceSpec, the document a supplier would actually send.

Channel decides the format: PDF (default), PNG for `image` (a phone photo of the paper invoice) and `whatsapp` (a
chat screenshot), plain text for `text`, `email` and `intent`.

When the spec carries `hidden_text`, a PDF hides it with one technique. Without an explicit `technique`, it is chosen
from the SHA-256 of the hidden text, so the same spec always renders the same way and a dataset with varied hidden
texts exercises every technique. Images draw it one shade off the background; plain text has nowhere to hide it.
"""

from __future__ import annotations

import hashlib
import re

from custodio.contracts import InvoiceSource, InvoiceSpec, RenderedDocument
from custodio.extraction.content import GREETING, TITLE, InvoiceContent, content_of
from custodio.extraction.errors import UnsupportedHiddenText
from custodio.extraction.render_pdf import PDF_TECHNIQUES, HiddenTechnique, render_pdf
from custodio.extraction.render_png import render_chat, render_photo

__all__ = ["PDF_TECHNIQUES", "HiddenTechnique", "render_invoice", "technique_for"]

_TEXT_CHANNELS = frozenset({InvoiceSource.TEXT, InvoiceSource.EMAIL, InvoiceSource.INTENT})
_NOT_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9-]+")


def render_invoice(spec: InvoiceSpec, *, technique: HiddenTechnique | None = None) -> RenderedDocument:
    content = content_of(spec)
    if spec.channel is InvoiceSource.IMAGE:
        return _document(spec, "png", "image/png", render_photo(content))
    if spec.channel is InvoiceSource.WHATSAPP:
        return _document(spec, "png", "image/png", render_chat(content))
    if spec.channel in _TEXT_CHANNELS:
        return _document(spec, "txt", "text/plain; charset=utf-8", _message(spec, content).encode())
    return _document(spec, "pdf", "application/pdf", render_pdf(content, technique or technique_for(spec)))


def technique_for(spec: InvoiceSpec) -> HiddenTechnique:
    """The technique a PDF uses to hide `spec.hidden_text`, picked from its SHA-256."""
    digest = hashlib.sha256((spec.hidden_text or "").encode()).digest()
    return PDF_TECHNIQUES[int.from_bytes(digest[:4]) % len(PDF_TECHNIQUES)]


def _document(spec: InvoiceSpec, extension: str, media_type: str, data: bytes) -> RenderedDocument:
    stem = _NOT_FILENAME_SAFE.sub("-", spec.invoice_number).strip("-")
    return RenderedDocument(filename=f"factura-{stem}.{extension}", media_type=media_type, data=data)


def _message(spec: InvoiceSpec, content: InvoiceContent) -> str:
    if content.hidden_text:
        raise UnsupportedHiddenText(f"Un mensaje de texto ({spec.channel}) no tiene dónde esconder texto.")
    subject = f"Asunto: Factura {content.number} de {content.supplier}" if spec.channel is InvoiceSource.EMAIL else None
    lines = (
        subject,
        "",
        content.note or GREETING,
        "",
        f"{TITLE.capitalize()} No. {content.number}",
        content.issue_line,
        content.due_line,
        f"Concepto: {content.description}",
        f"Total a pagar: {content.amount_text}",
        "",
        "Datos para el pago",
        *content.bank_lines,
        "",
        "Cordialmente,",
        content.supplier,
        content.tax_line,
    )
    return "\n".join(line for line in lines if line is not None).strip() + "\n"
