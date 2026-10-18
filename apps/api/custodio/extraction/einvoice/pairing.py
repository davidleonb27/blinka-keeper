"""The PDF (or image) and the XML of one invoice: the official XML wins, code compares the two.

A supplier usually sends both. The XML's values stand; the other document only fills what an XML never carries (a
CFDI has no bank account). If the two disagree on what is paid or to whom, someone altered one of them: the field is
distrusted, and so is everything taken from the other document, so a person looks before anything is paid.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from custodio.contracts import ExtractedField, ExtractedInvoice, InvoiceSource
from custodio.engine.text import normalize_code, normalize_name
from custodio.extraction import CRITICAL_FIELDS
from custodio.extraction.einvoice.reading import FAILED, PASSED, READER_PREFIX, distrusted
from custodio.extraction.source import SourceText
from custodio.extraction.structure import FIELD_KINDS
from custodio.extraction.verify import verified_field

COMPARED = (
    ("amount", "monto"),
    ("currency", "moneda"),
    ("supplier_tax_id", "identificación fiscal"),
    ("invoice_number", "número"),
    ("issue_date", "fecha de emisión"),
    ("account_number", "cuenta"),
)
DOCUMENT_NAMES = {InvoiceSource.PDF: "El PDF", InvoiceSource.IMAGE: "La imagen"}
OTHER_DOCUMENT = "El otro documento"


def is_einvoice_reading(reading: ExtractedInvoice) -> bool:
    return reading.reader.startswith(READER_PREFIX)


def same_invoice(official: ExtractedInvoice, other: ExtractedInvoice) -> bool:
    """Same invoice number and the same supplier, by tax id or by name."""
    number, other_number = official.invoice_number.value, other.invoice_number.value
    if not number or not other_number or normalize_code(number) != normalize_code(other_number):
        return False
    tax_id, other_tax_id = official.supplier_tax_id.value, other.supplier_tax_id.value
    if tax_id and other_tax_id and normalize_code(tax_id) == normalize_code(other_tax_id):
        return True
    name, other_name = official.supplier_name.value, other.supplier_name.value
    return bool(name and other_name and normalize_name(name) == normalize_name(other_name))


def merge(official: ExtractedInvoice, other: ExtractedInvoice) -> ExtractedInvoice:
    document = DOCUMENT_NAMES.get(other.source, OTHER_DOCUMENT)
    differences = [(name, label) for name, label in COMPARED if not _agree(name, official, other)]
    flagged = [_difference_line(document, label, official, other, name) for name, label in differences]
    compared = ", ".join(label for _, label in COMPARED)
    lines = flagged or [f"{PASSED} {document} coincide con el XML oficial en {compared}."]
    header = f"Cotejo con el documento que llegó junto ({other.reader}):"
    text = SourceText(pages=(official.visible_text, "\n".join([header, *lines]), other.visible_text))
    fields = {name: _merged_field(name, official, other, text, trusted=not differences) for name in FIELD_KINDS}
    for (name, _), line in zip(differences, flagged, strict=True):
        fields[name] = distrusted(fields[name], line, text)
    return official.model_copy(
        update={
            **fields,
            "visible_text": text.text,
            "sender_email": other.sender_email or official.sender_email,
            "hidden_findings": [*official.hidden_findings, *other.hidden_findings],
            "reader": f"{official.reader} + {other.reader}",
            "overall_confidence": min(fields[n].confidence if fields[n].verified else 0.0 for n in CRITICAL_FIELDS),
        }
    )


def _agree(name: str, official: ExtractedInvoice, other: ExtractedInvoice) -> bool:
    mine, theirs = getattr(official, name).value, getattr(other, name).value
    if mine is None or theirs is None:
        return True  # nothing to compare: the XML's value, or its absence, stands
    return SAME[name](mine, theirs)


def _same_amount(mine: str, theirs: str) -> bool:
    try:
        return Decimal(mine) == Decimal(theirs)
    except InvalidOperation:
        return False


def _same_code(mine: str, theirs: str) -> bool:
    return normalize_code(mine) == normalize_code(theirs)


def _same_text(mine: str, theirs: str) -> bool:
    return mine.strip().upper() == theirs.strip().upper()


SAME: dict[str, Callable[[str, str], bool]] = {
    "amount": _same_amount,
    "currency": _same_text,
    "supplier_tax_id": _same_code,
    "invoice_number": _same_code,
    "issue_date": _same_text,
    "account_number": _same_code,
}


def _difference_line(document: str, label: str, official: ExtractedInvoice, other: ExtractedInvoice, name: str) -> str:
    theirs, mine = getattr(other, name).value, getattr(official, name).value
    return (
        f"{FAILED} {document} dice {label} {theirs} y el XML oficial {mine}: "
        "manda el XML y una persona revisa por qué difieren antes de pagar."
    )


def _merged_field(
    name: str, official: ExtractedInvoice, other: ExtractedInvoice, text: SourceText, *, trusted: bool
) -> ExtractedField:
    """The XML's field as it was (its quote sits on the first page, unmoved); else the other one, verified again."""
    mine: ExtractedField = getattr(official, name)
    theirs: ExtractedField = getattr(other, name)
    if mine.value is not None or theirs.value is None:
        return mine
    quote = theirs.evidence.quote if theirs.evidence else None
    field = verified_field(
        FIELD_KINDS[name], value=theirs.value, quote=quote, confidence=theirs.confidence, source=text
    )
    return field if trusted else field.model_copy(update={"verified": False, "confidence": 0.0})
