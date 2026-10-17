import base64
import io
import zipfile
from decimal import Decimal
from xml.sax.saxutils import escape

import pytest

from custodio.ai import import_suppliers
from custodio.ai.suppliers import UnreadableSupplierFile, UnsupportedSupplierFile
from custodio.contracts import AgreementKind

from .conftest import FakeLLM, recorded

CSV_MEDIA = "text/csv"
XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SPANISH_ROWS = [
    [
        "Razón social",
        "NIT",
        "Banco",
        "Número de cuenta",
        "Moneda",
        "País",
        "Alias",
        "Tipo de acuerdo",
        "Monto acordado",
    ],
    [
        "Nube S.A.S.",
        "900.123.456-7",
        "Bancolombia",
        "123-456789-01",
        "usd",
        "co",
        "Nube Hosting|Nube",
        "tope mensual",
        "9.000",
    ],
    ["Inmobiliaria Andes", "800765432-1", "Davivienda", "55500011122", "USD", "CO", "", "fijo", "2.400,00"],
    ["Sin Cuenta Ltda.", "901000111-2", "BBVA", "", "COP", "CO", "", "", ""],
    ["Nube SAS", "9001234567", "Bancolombia", "999", "USD", "CO", "", "", ""],
    ["Datos Rápidos", "901555666-0", "Itaú", "778899", "COP", "CO", "", "", "1.500.000"],
]


def as_csv(rows: list[list[str]], delimiter: str = ";") -> bytes:
    return ("\n".join(delimiter.join(row) for row in rows) + "\n").encode("utf-8-sig")


def as_xlsx(rows: list[list[str]], *, preamble: str = "") -> bytes:
    """A minimal workbook: shared strings for the header, inline strings and numbers for the body."""
    header, *body = rows
    shared = "".join(f"<si><t>{escape(cell)}</t></si>" for cell in header)
    columns = "ABCDEFGHIJ"

    def cell(ref: str, value: str, index: int | None) -> str:
        if index is not None:
            return f'<c r="{ref}" t="s"><v>{index}</v></c>'
        if value.isdigit():
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>' if value else ""

    xml_rows = ['<row r="1">' + "".join(cell(f"{columns[i]}1", v, i) for i, v in enumerate(header)) + "</row>"]
    for n, row in enumerate(body, start=2):
        xml_rows.append(
            f'<row r="{n}">' + "".join(cell(f"{columns[i]}{n}", v, None) for i, v in enumerate(row)) + "</row>"
        )
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets><sheet name="Proveedores" sheetId="1" r:id="rId1"/>'
            "</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>',
        )
        archive.writestr("xl/sharedStrings.xml", f'{preamble}<sst xmlns="{main}">{shared}</sst>')
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{main}"><sheetData>{"".join(xml_rows)}</sheetData></worksheet>',
        )
    return buffer.getvalue()


def assert_spanish_rows_imported(result_names: list[str], warnings: list[str]) -> None:
    assert result_names == ["Nube S.A.S.", "Inmobiliaria Andes", "Datos Rápidos"]
    assert any("Fila 4" in w and "cuenta" in w for w in warnings)
    assert any("Fila 5" in w and "duplicad" in w for w in warnings)
    assert any("Fila 6" in w and "tipo de acuerdo" in w for w in warnings)


def test_a_spanish_csv_is_read_by_code_with_warnings(fake_llm: FakeLLM) -> None:
    result = import_suppliers(as_csv(SPANISH_ROWS), filename="proveedores.csv", media_type=CSV_MEDIA)

    assert fake_llm.calls == []
    assert_spanish_rows_imported([b.name for b in result.beneficiaries], result.warnings)
    nube, andes, datos = result.beneficiaries
    assert nube.id == "nube-sas"
    assert nube.tax_id == "900.123.456-7"
    assert nube.account_number == "12345678901"
    assert nube.currency == "USD"
    assert nube.country == "CO"
    assert nube.aliases == ["Nube Hosting", "Nube"]
    assert nube.agreement is not None
    assert nube.agreement.kind is AgreementKind.MONTHLY_CAP
    assert nube.agreement.amount == Decimal("9000")
    assert nube.agreement.currency == "USD"
    assert nube.agreement.source == "proveedores.csv, fila 2"
    assert andes.agreement is not None
    assert andes.agreement.kind is AgreementKind.FIXED
    assert andes.agreement.amount == Decimal("2400")
    assert datos.agreement is None


def test_a_comma_csv_with_english_headers_is_read(fake_llm: FakeLLM) -> None:
    rows = [
        ["name", "tax_id", "bank", "account", "currency"],
        ["Acme Corp", "US-77", "Chase", "000111222", "USD"],
    ]

    result = import_suppliers(as_csv(rows, ","), filename="vendors.csv", media_type="text/csv")

    assert [b.name for b in result.beneficiaries] == ["Acme Corp"]
    assert result.warnings == []


def test_an_invalid_currency_is_a_warning(fake_llm: FakeLLM) -> None:
    rows = [SPANISH_ROWS[0], ["Moneda Rara", "901999888-1", "Itaú", "445566", "pesos", "CO", "", "", ""]]

    result = import_suppliers(as_csv(rows), filename="p.csv", media_type=CSV_MEDIA)

    assert result.beneficiaries == []
    assert any("Fila 2" in w and "moneda" in w for w in result.warnings)


def test_a_csv_without_recognizable_columns_is_unreadable(fake_llm: FakeLLM) -> None:
    with pytest.raises(UnreadableSupplierFile, match="cuenta"):
        import_suppliers(b"foo;bar\n1;2\n", filename="p.csv", media_type=CSV_MEDIA)


def test_an_xlsx_is_read_by_code_like_a_csv(fake_llm: FakeLLM) -> None:
    result = import_suppliers(as_xlsx(SPANISH_ROWS), filename="proveedores.xlsx", media_type=XLSX_MEDIA)

    assert fake_llm.calls == []
    assert_spanish_rows_imported([b.name for b in result.beneficiaries], result.warnings)
    assert result.beneficiaries[1].account_number == "55500011122"


def test_an_xlsx_with_a_doctype_is_refused(fake_llm: FakeLLM) -> None:
    hostile = as_xlsx(SPANISH_ROWS, preamble='<!DOCTYPE lol [<!ENTITY a "aaaa">]>')

    with pytest.raises(UnreadableSupplierFile):
        import_suppliers(hostile, filename="p.xlsx", media_type=XLSX_MEDIA)


def test_a_file_that_is_not_a_workbook_is_unreadable(fake_llm: FakeLLM) -> None:
    with pytest.raises(UnreadableSupplierFile):
        import_suppliers(b"not a zip", filename="p.xlsx", media_type=XLSX_MEDIA)


def test_a_pdf_is_read_by_the_model_and_validated_by_code(fake_llm: FakeLLM) -> None:
    pdf = b"%PDF-1.4 contract"
    fake_llm.reply(recorded("suppliers_pdf_incomplete"))

    result = import_suppliers(pdf, filename="contrato-nube.pdf", media_type="application/pdf")

    call = fake_llm.calls[0]
    assert call.model == "claude-sonnet-5-5"
    assert call.effort == "medium"
    assert call.content[0]["type"] == "document"
    assert call.content[0]["source"]["data"] == base64.b64encode(pdf).decode()
    [nube] = result.beneficiaries
    assert nube.account_number == "12345678901"
    assert nube.agreement is not None
    assert nube.agreement.amount == Decimal("9000")
    assert nube.agreement.source == "contrato-nube.pdf: «Cláusula 4: el valor mensual no superará USD 9.000»"
    assert len(result.warnings) == 3
    assert any("Proveedor 2" in w and "cuenta" in w for w in result.warnings)


def test_other_file_types_are_refused(fake_llm: FakeLLM) -> None:
    with pytest.raises(UnsupportedSupplierFile):
        import_suppliers(b"\x89PNG", filename="foto.png", media_type="image/png")
