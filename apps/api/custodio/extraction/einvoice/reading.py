"""An electronic invoice into an ExtractedInvoice, by code alone: no model reads or decides anything here.

The reading's text is what the acta shows: every field on its own line with its path in the XML, then the checks code
ran and what was not checked. Each field's quote is its line, so `verify` finds it and the acta highlights it; a failed
check replaces the quote of the field it distrusts with the line that says why.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from custodio.contracts import (
    Evidence,
    ExtractedField,
    ExtractedInvoice,
    HiddenTextFinding,
    HiddenTextKind,
    InvoiceSource,
)
from custodio.engine.domains import first_email
from custodio.extraction import CRITICAL_FIELDS
from custodio.extraction.einvoice import cfdi, dian, safe_xml
from custodio.extraction.einvoice.checks import DOCUMENT_FIELD, CheckResult, nit_text, run_checks
from custodio.extraction.einvoice.errors import NotAnEInvoice
from custodio.extraction.einvoice.model import EInvoice, XmlValue
from custodio.extraction.instructions import find_instructions
from custodio.extraction.source import SourceText
from custodio.extraction.structure import FIELD_KINDS
from custodio.extraction.verify import locate, verified_field

HEADER = "Leída de la factura electrónica oficial (sin IA)"
READER_PREFIX = "factura electrónica oficial"
CHECKS_HEADER = "Comprobaciones hechas por código, sin IA:"
NOTES_HEADER = "Notas del documento:"
PASSED, FAILED = "✓", "✗"
XML_CONFIDENCE = 1.0  # read from a structured field, not interpreted; a failed check still drops it to zero
HIDDEN_DETAIL = "Texto dentro del XML que no es un campo de la factura y está dirigido al agente"
PARSERS: tuple[tuple[Callable[[Element], bool], Callable[[Element], EInvoice]], ...] = (
    (dian.handles, dian.parse),
    (cfdi.handles, cfdi.parse),
)


@dataclass(frozen=True)
class FieldLine:
    name: str  # the ExtractedInvoice field, or "" for a line that only informs
    label: str
    value: XmlValue
    shown: str  # how the acta writes it, e.g. a NIT with its dots and check digit

    @property
    def line(self) -> str:
        return f"{self.label}: {self.shown} [{self.value.path}]"


def read_einvoice(
    data: bytes, *, document_id: str, company_name: str | None, source: InvoiceSource = InvoiceSource.TEXT
) -> ExtractedInvoice:
    """Raises UnsafeXml, UnreadableDocument or NotAnEInvoice; it never guesses a value."""
    invoice = parse_einvoice(safe_xml.parse(data))
    checks = run_checks(invoice, company_name)
    lines = _field_lines(invoice)
    text = SourceText(pages=(_document_text(invoice, lines, checks),))
    fields = {name: _field(name, lines, text) for name in FIELD_KINDS}
    for check in reversed(checks):  # the first failure of a field is the one its quote shows
        if not check.passed and check.field:
            # The engine skips an absent optional field (a tax id), so its failure falls on what would be paid.
            name = check.field if fields[check.field].value is not None else DOCUMENT_FIELD
            fields[name] = distrusted(fields[name], f"{FAILED} {check.line}", text)
    return ExtractedInvoice.model_validate(
        {
            "document_id": document_id,
            "source": source,
            **fields,
            "visible_text": text.text,
            "sender_email": first_email(text.text),
            "hidden_findings": [*find_instructions(text), *_instructions_outside_fields(invoice, text)],
            "reader": f"{READER_PREFIX} {invoice.standard.value} (XML, sin IA)",
            "overall_confidence": min(
                fields[name].confidence if fields[name].verified else 0.0 for name in CRITICAL_FIELDS
            ),
        }
    )


def parse_einvoice(root: Element) -> EInvoice:
    for handles, parse in PARSERS:
        if handles(root):
            return parse(root)
    raise NotAnEInvoice("El XML no es una factura electrónica de la DIAN (UBL 2.1) ni un CFDI 4.0 del SAT.")


def _field_lines(invoice: EInvoice) -> list[FieldLine]:
    supplier, customer = invoice.supplier, invoice.customer
    candidates: list[tuple[str, str, XmlValue | None]] = [
        ("", invoice.unique_id_label, invoice.unique_id),
        ("invoice_number", "Número", invoice.number),
        ("issue_date", "Fecha de emisión", invoice.issue_date),
        ("due_date", "Fecha de vencimiento", invoice.due_date),
        ("supplier_name", "Emisor", supplier.name),
        ("supplier_tax_id", "Identificación fiscal del emisor", supplier.tax_id),
        ("", "Receptor", customer.name),
        ("", "Identificación fiscal del receptor", customer.tax_id),
        ("currency", "Moneda", invoice.currency),
        ("", "Tipo de cambio", invoice.exchange_rate),
        *(("", term.label.capitalize(), term.value) for term in invoice.terms),
        ("amount", "Total a pagar", invoice.total),
        ("", "Forma de pago", invoice.payment_form),
        ("bank_name", "Banco", invoice.bank_name),
        ("account_number", "Cuenta", invoice.account),
        ("description", "Descripción", invoice.description),
    ]
    return [FieldLine(name, label, value, _shown(invoice, name, value)) for name, label, value in candidates if value]


def _shown(invoice: EInvoice, name: str, value: XmlValue) -> str:
    supplier = invoice.supplier
    if name == "supplier_tax_id" and supplier.is_nit:
        return nit_text("".join(char for char in value.text if char.isdigit()), supplier.check_digit)
    if name == "amount" and invoice.currency:
        return f"{value.text} {invoice.currency.text}"
    return value.text


def _document_text(invoice: EInvoice, lines: list[FieldLine], checks: list[CheckResult]) -> str:
    parts = [HEADER, f"Documento: {invoice.title}", *(line.line for line in lines), "", CHECKS_HEADER]
    parts += [f"{PASSED if check.passed else FAILED} {check.line}" for check in checks]
    parts.append(
        f"No se consultó {invoice.authority} ni se verificó la firma digital: Blinka Keeper no se conecta a servicios "
        "externos; lo de arriba se comprobó sobre el contenido del XML."
    )
    if invoice.notes:
        parts += ["", NOTES_HEADER, *invoice.notes]
    return "\n".join(parts)


def _field(name: str, lines: list[FieldLine], text: SourceText) -> ExtractedField:
    found = next((line for line in lines if line.name == name), None)
    if found is None:
        return ExtractedField(value=None, confidence=0.0)
    value = found.shown if name == "supplier_tax_id" else found.value.text
    return verified_field(FIELD_KINDS[name], value=value, quote=found.line, confidence=XML_CONFIDENCE, source=text)


def distrusted(field: ExtractedField, line: str, text: SourceText) -> ExtractedField:
    """The field keeps its value but not its trust: its quote becomes the line in `text` that says why."""
    span = locate(line, text.text)
    start, end = span if span else (None, None)
    evidence = Evidence(
        quote=line, page=text.page_at(start) if start is not None else None, char_start=start, char_end=end
    )
    return ExtractedField(value=field.value, evidence=evidence, confidence=0.0, verified=False)


def _instructions_outside_fields(invoice: EInvoice, text: SourceText) -> list[HiddenTextFinding]:
    """Text addressed to the agent anywhere in the XML, even in elements the acta does not show."""
    found = find_instructions(SourceText(pages=(invoice.all_text,)))
    return [
        HiddenTextFinding(kind=HiddenTextKind.METADATA, text=finding.text, detail=HIDDEN_DETAIL)
        for finding in found
        if finding.text not in text.text
    ]
