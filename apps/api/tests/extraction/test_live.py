"""End-to-end reading with the real models. Run with CUSTODIO_LIVE_TESTS=1 uv run pytest -m live -s.

Ten rendered documents (fixtures/documents/specs.json) are read by the full pipeline and compared with the specs
that produced them. A field counts as correct only when its value matches and code verified its quote; for the
ambiguous "$" invoice, the correct outcome for currency is "not verified".
"""

import json
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest
from google import genai
from pydantic import TypeAdapter

from custodio.config import get_settings
from custodio.contracts import ExtractedField, ExtractedInvoice, HiddenTextKind, InvoiceSource, InvoiceSpec
from custodio.extraction import extract_document, extract_text, render_invoice
from custodio.extraction.structure import FIELD_KINDS
from custodio.extraction.text import fold

pytestmark = pytest.mark.live

SPECS = TypeAdapter(list[InvoiceSpec]).validate_json(
    (Path(__file__).parents[1] / "fixtures" / "documents" / "specs.json").read_text()
)
TEXT_CHANNELS = {InvoiceSource.TEXT, InvoiceSource.EMAIL, InvoiceSource.INTENT}
MIN_FIELD_ACCURACY = 0.9


def read(spec: InvoiceSpec, document_id: str) -> ExtractedInvoice:
    document = render_invoice(spec)
    if spec.channel in TEXT_CHANNELS:
        return extract_text(document.data.decode(), document_id=document_id, source=spec.channel)
    return extract_document(
        document.data, filename=document.filename, media_type=document.media_type, document_id=document_id
    )


def digits(text: str) -> str:
    return "".join(char for char in text if char.isdigit())


def letters_and_digits(text: str) -> str:
    return "".join(char for char in text if char.isalnum()).upper()


def same_amount(read_value: str, expected: str) -> bool:
    try:
        return Decimal(read_value) == Decimal(expected)
    except InvalidOperation:
        return False


COMPARE: dict[str, Callable[[str, str], bool]] = {
    "supplier_name": lambda got, want: fold(got) == fold(want),
    "supplier_tax_id": lambda got, want: digits(got) == digits(want),
    "invoice_number": lambda got, want: letters_and_digits(got) == letters_and_digits(want),
    "issue_date": str.__eq__,
    "due_date": str.__eq__,
    "amount": same_amount,
    "currency": str.__eq__,
    "bank_name": lambda got, want: fold(got) == fold(want),
    "account_number": lambda got, want: digits(got) == digits(want),
    "description": lambda got, want: fold(got) == fold(want),
}


def expected_value(spec: InvoiceSpec, name: str) -> str | None:
    value = getattr(spec, name)
    return None if value is None else (value.isoformat() if hasattr(value, "isoformat") else str(value))


def is_correct(spec: InvoiceSpec, name: str, field: ExtractedField) -> bool:
    if name == "currency" and spec.amount_text and "$" in spec.amount_text:
        return not field.verified
    want = expected_value(spec, name)
    if want is None:
        return field.value is None
    return field.verified and field.value is not None and COMPARE[name](field.value, want)


@pytest.fixture
def claude_key() -> None:
    if not get_settings().anthropic_configured:
        pytest.skip("NO MEDIDO: falta ANTHROPIC_API_KEY")


@pytest.fixture
def gemini_key() -> None:
    if not get_settings().gemini_configured:
        pytest.skip("NO MEDIDO: falta GEMINI_API_KEY")


def test_the_configured_gemini_model_is_listed(gemini_key: None) -> None:
    names = [model.name or "" for model in genai.Client().models.list()]
    flash = sorted(name for name in names if re.search(r"gemini-[\d.]+-flash", name))
    print("\nGemini flash models:", json.dumps(flash, indent=1))
    assert f"models/{get_settings().gemini_model}" in names


def test_one_rendered_pdf_is_read_end_to_end(claude_key: None) -> None:
    invoice = read(SPECS[0], "live-0")
    print("\n", invoice.model_dump_json(indent=1, exclude={"visible_text"}))
    assert invoice.amount.verified and invoice.amount.value == "4200000.00"


def test_ten_rendered_documents_per_field_accuracy(claude_key: None, gemini_key: None) -> None:
    invoices = [read(spec, f"live-{number}") for number, spec in enumerate(SPECS)]

    accuracy = {
        name: sum(is_correct(spec, name, getattr(invoice, name)) for spec, invoice in zip(SPECS, invoices, strict=True))
        / len(SPECS)
        for name in FIELD_KINDS
    }
    print("\n| Campo | Exactitud |\n|---|---|")
    for name, share in accuracy.items():
        print(f"| {name} | {share:.0%} |")
    for number, (spec, invoice) in enumerate(zip(SPECS, invoices, strict=True)):
        wrong = [name for name in FIELD_KINDS if not is_correct(spec, name, getattr(invoice, name))]
        print(
            f"doc {number} ({spec.channel}, {invoice.reader}): mal={wrong} hallazgos="
            f"{[finding.kind.value for finding in invoice.hidden_findings]}"
        )

    hidden = [invoice for spec, invoice in zip(SPECS, invoices, strict=True) if spec.hidden_text]
    assert all(invoice.hidden_findings for invoice in hidden)
    instructed = [invoice for spec, invoice in zip(SPECS, invoices, strict=True) if spec.note and "IA" in spec.note]
    assert all(HiddenTextKind.INSTRUCTION in {f.kind for f in invoice.hidden_findings} for invoice in instructed)
    assert min(accuracy.values()) >= MIN_FIELD_ACCURACY
