"""A perfect reading of an InvoiceSpec: the document text and an extraction whose every quote is found in it.

This stands in for lane L2's pipeline so the engine and the UI work without any model. Quotes are verified by code
here too: a field is `verified` only if its quote is literally in the document text.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal

from custodio.contracts import (
    Evidence,
    ExtractedField,
    ExtractedInvoice,
    HiddenTextFinding,
    HiddenTextKind,
    InvoiceSource,
    InvoiceSpec,
)

READER = "dataset"
HIDDEN_DETAIL = "Texto blanco sobre fondo blanco, invisible para una persona"
CHANNEL_CONFIDENCE = {
    InvoiceSource.PDF: 0.98,
    InvoiceSource.EMAIL: 0.98,
    InvoiceSource.TEXT: 0.98,
    InvoiceSource.INTENT: 0.99,
    InvoiceSource.WHATSAPP: 0.97,
    InvoiceSource.IMAGE: 0.93,
}
CHAT_CHANNELS = (InvoiceSource.WHATSAPP, InvoiceSource.IMAGE)
WHOLE_UNITS = ("COP", "CLP")  # written without cents, Latin style: 4.200.000
LATIN_DECIMALS = ("BRL",)  # written Latin style with cents: 9.800,00
NUMBER = re.compile(r"\d[\d.,]*")


def written_amount(amount: Decimal, currency: str) -> str:
    """How the dataset writes a total: `USD 4,800.00`, `COP 9.200.000`, `BRL 9.800,00`."""
    if currency in WHOLE_UNITS:
        return f"{currency} {amount:,.0f}".replace(",", ".")
    english = f"{amount:,.2f}"
    if currency in LATIN_DECIMALS:
        english = english.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return f"{currency} {english}"


def document_text(spec: InvoiceSpec, *, customer: str) -> str:
    header = "Cuenta de cobro No." if spec.channel in CHAT_CHANNELS else "FACTURA N°"
    lines = (
        f"{header} {spec.invoice_number}",
        f"Emisor: {spec.supplier_name}",
        f"{spec.tax_label}: {spec.supplier_tax_id}",
        f"Cliente: {customer}",
        f"Fecha de emisión: {spec.issue_date.isoformat()}",
        f"Vence: {spec.due_date.isoformat()}" if spec.due_date else None,
        f"Concepto: {spec.description}",
        f"Total: {spec.amount_text or written_amount(spec.amount, spec.currency)}",
        f"Pagar a: {spec.bank_name} · cuenta {spec.account_number}",
        spec.note,
    )
    return "\n".join(line for line in lines if line)


def read_spec(
    spec: InvoiceSpec, *, document_id: str, customer: str, confidence: Mapping[str, float]
) -> ExtractedInvoice:
    text = document_text(spec, customer=customer)
    base = CHANNEL_CONFIDENCE[spec.channel]

    def field(name: str, value: str | None, quote: str | None = None) -> ExtractedField:
        cited = quote if quote is not None else value
        evidence = Evidence(quote=cited, page=1) if cited is not None else None
        verified = cited is not None and cited in text
        return ExtractedField(value=value, evidence=evidence, confidence=confidence.get(name, base), verified=verified)

    total = spec.amount_text or written_amount(spec.amount, spec.currency)
    number = NUMBER.search(total)
    fields = {
        "supplier_name": field("supplier_name", spec.supplier_name),
        "supplier_tax_id": field("supplier_tax_id", spec.supplier_tax_id),
        "invoice_number": field("invoice_number", spec.invoice_number),
        "issue_date": field("issue_date", spec.issue_date.isoformat()),
        "due_date": field("due_date", spec.due_date.isoformat() if spec.due_date else None),
        "amount": field("amount", f"{spec.amount:.2f}", number.group() if number else total),
        "currency": field("currency", spec.currency, spec.currency if spec.amount_text is None else total),
        "bank_name": field("bank_name", spec.bank_name),
        "account_number": field("account_number", spec.account_number),
        "description": field("description", spec.description),
    }
    return ExtractedInvoice(
        document_id=document_id,
        source=spec.channel,
        visible_text=text,
        hidden_findings=_hidden(spec),
        reader=READER,
        overall_confidence=min(f.confidence for f in fields.values() if f.value is not None),
        **fields,
    )


def _hidden(spec: InvoiceSpec) -> list[HiddenTextFinding]:
    if spec.hidden_text is None:
        return []
    return [HiddenTextFinding(kind=HiddenTextKind.INVISIBLE_COLOR, text=spec.hidden_text, page=1, detail=HIDDEN_DETAIL)]
