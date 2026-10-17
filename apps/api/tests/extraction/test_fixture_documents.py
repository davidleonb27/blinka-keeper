"""The ten live-test documents, read by an ideal model: code must verify every field a faithful reading quotes."""

from pathlib import Path

import pytest
from pydantic import TypeAdapter

from custodio import llm
from custodio.contracts import InvoiceSource, InvoiceSpec
from custodio.extraction import extract_document, render_invoice
from custodio.extraction.content import content_of
from custodio.extraction.structure import InvoiceReading, QuotedValue
from tests.extraction.doubles import FakeClaude

SPECS = TypeAdapter(list[InvoiceSpec]).validate_json(
    (Path(__file__).parents[1] / "fixtures" / "documents" / "specs.json").read_text()
)


def ideal_reading(spec: InvoiceSpec) -> InvoiceReading:
    content = content_of(spec)
    ambiguous = spec.amount_text is not None
    quotes: dict[str, tuple[str | None, str | None]] = {
        "supplier_name": (spec.supplier_name, spec.supplier_name),
        "supplier_tax_id": (spec.supplier_tax_id, content.tax_line),
        "invoice_number": (spec.invoice_number, spec.invoice_number),
        "issue_date": (spec.issue_date.isoformat(), content.issue_line),
        "due_date": (spec.due_date.isoformat(), content.due_line) if spec.due_date else (None, None),
        "amount": (f"{spec.amount:.2f}", content.amount_text),
        "currency": (spec.currency, content.amount_text),
        "bank_name": (spec.bank_name, content.bank_lines[0]),
        "account_number": (spec.account_number, content.bank_lines[1]),
        "description": (spec.description, spec.description),
    }
    return InvoiceReading(
        **{
            name: QuotedValue(value=value, quote=quote, confidence=0.3 if ambiguous and name == "currency" else 0.95)
            for name, (value, quote) in quotes.items()
        }
    )


@pytest.mark.parametrize("spec", SPECS, ids=[spec.invoice_number for spec in SPECS])
def test_an_ideal_reading_of_each_fixture_document_verifies(monkeypatch: pytest.MonkeyPatch, spec: InvoiceSpec) -> None:
    transcript = render_invoice(spec.model_copy(update={"channel": InvoiceSource.TEXT, "hidden_text": None}))
    monkeypatch.setattr(
        llm, "structured", FakeClaude(reading=ideal_reading(spec), transcription=transcript.data.decode())
    )
    document = render_invoice(spec)

    invoice = extract_document(
        document.data, filename=document.filename, media_type=document.media_type, document_id=spec.invoice_number
    )

    unverified = {name for name in InvoiceReading.model_fields if not getattr(invoice, name).verified}
    expected = ({"currency"} if spec.amount_text else set()) | (set() if spec.due_date else {"due_date"})
    assert unverified == expected
    assert bool(invoice.hidden_findings) == bool(spec.hidden_text or (spec.note and "IA" in spec.note))
