"""Reading invoices: documents in, `ExtractedInvoice` out. Owned by lane L2.

The model reads; code verifies. Every extracted value carries the exact quote that supports it, and
`ExtractedField.verified` is set by code only after finding that quote in the source text. Hidden text is
detected by code (character colors, sizes and positions), never by asking a model whether text is hidden.
"""

from __future__ import annotations

from custodio.contracts import ExtractedInvoice, InvoiceSource, InvoiceSpec, RenderedDocument


def extract_document(data: bytes, *, filename: str, media_type: str, document_id: str) -> ExtractedInvoice:
    """Read a PDF or an image (png, jpeg, webp) into an ExtractedInvoice."""
    raise NotImplementedError("lane L2")


def extract_text(text: str, *, document_id: str, source: InvoiceSource = InvoiceSource.TEXT) -> ExtractedInvoice:
    """Read a plain-text invoice (email body, WhatsApp message, payment intent text)."""
    raise NotImplementedError("lane L2")


def render_invoice(spec: InvoiceSpec) -> RenderedDocument:
    """Render a spec as a realistic document (PDF by default), including its hidden text if any."""
    raise NotImplementedError("lane L2")
