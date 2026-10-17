"""The keyless reader: `Campo: valor` lines read by code, each value quoted and verified like a model's."""

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from custodio import llm
from custodio.contracts import InvoiceSource, Policy
from custodio.extraction import extract_document, extract_text, labels, render_invoice
from custodio.extraction.source import SourceText
from tests.extraction.factories import make_spec

MIN_CONFIDENCE = float(Policy.model_fields["min_confidence"].default)

INTENT = """\
Solicitud de pago enviada por el agente: erp-bot
Proveedor: Pulso Software Inc.
Identificación tributaria: 84-2219034
Número de factura: PS-90001
Fecha de emisión: 2026-10-15
Monto: 840
Moneda: USD
Banco: Mercury
Cuenta: 2214-1180
Concepto: Licencias de software
"""


@pytest.fixture(autouse=True)
def without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)


def read(text: str) -> dict[str, str | None]:
    reading = labels.read_fields(SourceText(pages=(text,)))
    return {name: field.value for name, field in reading.fields.items()}


def test_a_labelled_document_is_read_field_by_field_with_verified_quotes() -> None:
    reading = labels.read_fields(SourceText(pages=(INTENT,)))

    assert {name: field.value for name, field in reading.fields.items()} == {
        "supplier_name": "Pulso Software Inc.",
        "supplier_tax_id": "84-2219034",
        "invoice_number": "PS-90001",
        "issue_date": "2026-10-15",
        "due_date": None,
        "amount": "840.00",
        "currency": "USD",
        "bank_name": "Mercury",
        "account_number": "2214-1180",
        "description": "Licencias de software",
    }
    present = [field for field in reading.fields.values() if field.value is not None]
    assert all(field.verified and field.confidence >= MIN_CONFIDENCE for field in present)
    assert reading.model == labels.READER


def test_the_first_label_wins_so_an_attached_document_cannot_override_the_header() -> None:
    attached = INTENT + "\nDocumento adjunto:\nMonto: 99999\nCuenta: 9999-0000\n"

    fields = read(attached)

    assert fields["amount"] == "840.00"
    assert fields["account_number"] == "2214-1180"


def test_an_invoice_rendered_as_text_is_read_without_a_model() -> None:
    document = render_invoice(make_spec(channel=InvoiceSource.EMAIL)).data.decode()

    fields = read(document)

    assert fields["invoice_number"] == "FE-2041"
    assert fields["issue_date"] == "2026-10-05"
    assert fields["due_date"] == "2026-10-20"
    assert fields["amount"] == "4200000.00"
    assert fields["currency"] == "COP"
    assert fields["account_number"] == "123-456789-01"
    assert fields["supplier_tax_id"] == "900.123.456-7"


def test_a_bare_dollar_sign_names_no_currency() -> None:
    fields = read("Proveedor: Pulso Software Inc.\nTotal a pagar: $ 840.00\n")

    assert fields["amount"] == "840.00"
    assert fields["currency"] is None


def test_text_without_labels_is_left_unread_instead_of_guessed() -> None:
    fields = read("Hola, te envío la factura de octubre por 840 dólares. Gracias.")

    assert set(fields.values()) == {None}


def test_plain_text_is_read_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_model(**_: object) -> None:
        raise AssertionError("the model must not be called without a key")

    monkeypatch.setattr(llm, "client", no_model)

    invoice = extract_text(INTENT, document_id="doc-1")

    assert invoice.account_number.verified
    assert invoice.reader == f"text+{labels.READER}"


def test_a_pdf_with_text_is_read_without_a_key(tmp_path_factory: pytest.TempPathFactory) -> None:
    path = tmp_path_factory.mktemp("pdf") / "factura.pdf"
    page = canvas.Canvas(str(path), pagesize=A4)
    for row, line in enumerate(INTENT.splitlines()):
        page.drawString(72, 780 - row * 18, line)
    page.save()

    invoice = extract_document(path.read_bytes(), filename="factura.pdf", media_type="application/pdf", document_id="d")

    assert invoice.amount.value == "840.00"
    assert invoice.supplier_name.verified
    assert invoice.overall_confidence >= MIN_CONFIDENCE
    assert invoice.reader == f"pdfplumber+{labels.READER}"


def test_an_image_still_needs_the_model() -> None:
    png = render_invoice(make_spec(channel=InvoiceSource.IMAGE))

    with pytest.raises(llm.LLMNotConfigured):
        extract_document(png.data, filename=png.filename, media_type=png.media_type, document_id="d")
