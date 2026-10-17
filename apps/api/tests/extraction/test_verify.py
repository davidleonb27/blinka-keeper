from datetime import date

import pytest

from custodio.extraction.dates import dates_in
from custodio.extraction.source import SourceText
from custodio.extraction.verify import FieldKind, locate, normalize_value, supports


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Fecha: 2026-10-05", {date(2026, 10, 5)}),
        ("Fecha de emisión: 05/10/2026", {date(2026, 10, 5)}),  # day first, as Latin invoices write it
        ("Vence 5.10.2026", {date(2026, 10, 5)}),
        ("5 de octubre de 2026", {date(2026, 10, 5)}),
        ("05-oct-2026", {date(2026, 10, 5)}),
        ("1 Sept 2026", {date(2026, 9, 1)}),
        ("October 5, 2026", {date(2026, 10, 5)}),
        ("Del 01/10/2026 al 31/10/2026", {date(2026, 10, 1), date(2026, 10, 31)}),
        ("31/02/2026", set()),  # not a date
        ("sin fecha", set()),
    ],
)
def test_dates_in_reads_the_formats_invoices_use(text: str, expected: set[date]) -> None:
    assert dates_in(text) == expected


SUPPORT_CASES = [
    # text: the value appears in the quote, ignoring case, accents and spacing
    (FieldKind.TEXT, "Acme Cloud S.A.S.", "Proveedor: ACME  CLOUD S.A.S.", True),
    (FieldKind.TEXT, "Compañía Andina", "COMPANIA ANDINA LTDA", True),
    (FieldKind.TEXT, "Acme Cloud", "Proveedor: Beta Ltda", False),
    # identifiers: same letters and digits in order, separators free, not part of a longer code
    (FieldKind.IDENTIFIER, "FE-1234", "Factura No. FE 1234", True),
    (FieldKind.IDENTIFIER, "FE-123", "Factura No. FE-1234", False),
    (FieldKind.IDENTIFIER, "fe-1234", "FE-1234", True),
    # digits: tax ids and accounts compare digits only
    (FieldKind.DIGITS, "900123456-7", "NIT 900.123.456-7", True),
    (FieldKind.DIGITS, "12345678901", "Cuenta de ahorros No. 123-456789-01", True),
    (FieldKind.DIGITS, "12345678901", "Cuenta de ahorros No. 123-456789-02", False),
    (FieldKind.DIGITS, "4567", "Cuenta 1234567", False),
    (FieldKind.DIGITS, "N/A", "Cuenta N/A", False),
    # amounts: some amount in the quote parses to the same number
    (FieldKind.AMOUNT, "4200000.00", "Total a pagar: $ 4.200.000,00", True),
    (FieldKind.AMOUNT, "4200000.00", "TOTAL USD 4,200,000.00", True),
    (FieldKind.AMOUNT, "420000.00", "Total a pagar: $ 4.200.000,00", False),
    (FieldKind.AMOUNT, "1000.00", "$ 1.000", True),
    # dates: some date in the quote is the same day
    (FieldKind.DATE, "2026-10-05", "Fecha de emisión: 05/10/2026", True),
    (FieldKind.DATE, "2026-05-10", "Fecha de emisión: 05/10/2026", False),
    (FieldKind.DATE, "2026-10-05", "5 de octubre de 2026", True),
    # currency: needs an explicit marker; a bare "$" supports nothing
    (FieldKind.CURRENCY, "COP", "COP 4.200.000", True),
    (FieldKind.CURRENCY, "USD", "US$ 300", True),
    (FieldKind.CURRENCY, "COP", "$ 4.200.000", False),
    (FieldKind.CURRENCY, "USD", "COP 4.200.000", False),
]


@pytest.mark.parametrize(("kind", "value", "quote", "expected"), SUPPORT_CASES)
def test_supports_checks_the_quote_backs_the_value(kind: FieldKind, value: str, quote: str, expected: bool) -> None:
    assert supports(kind, value, quote) is expected


@pytest.mark.parametrize(
    ("kind", "raw", "expected"),
    [
        (FieldKind.AMOUNT, "4200000", "4200000.00"),
        (FieldKind.AMOUNT, "12.5", "12.50"),
        (FieldKind.AMOUNT, "0.125", "0.125"),
        (FieldKind.AMOUNT, "4.200.000", None),  # must already be a plain decimal
        (FieldKind.AMOUNT, "-5.00", None),
        (FieldKind.DATE, "2026-10-05", "2026-10-05"),
        (FieldKind.DATE, "05/10/2026", None),
        (FieldKind.CURRENCY, " cop ", "COP"),
        (FieldKind.CURRENCY, "$", None),
        (FieldKind.CURRENCY, "PESOS", None),
        (FieldKind.TEXT, "  Acme Cloud  ", "Acme Cloud"),
        (FieldKind.TEXT, "   ", None),
        (FieldKind.DIGITS, None, None),
    ],
)
def test_normalize_value_keeps_only_canonical_forms(kind: FieldKind, raw: str | None, expected: str | None) -> None:
    assert normalize_value(kind, raw) == expected


def test_locate_finds_the_quote_with_any_spacing_and_returns_the_original_span() -> None:
    source = "FACTURA FE-1\nTotal a pagar:   COP 4.200.000,00\nGracias"
    span = locate("Total a pagar: COP\n4.200.000,00", source)
    assert span is not None
    assert source[span[0] : span[1]] == "Total a pagar:   COP 4.200.000,00"


@pytest.mark.parametrize("quote", ["Total a pagar: COP 9.999.999,00", "", "   "])
def test_locate_returns_none_when_the_quote_is_not_in_the_source(quote: str) -> None:
    assert locate(quote, "Total a pagar: COP 4.200.000,00") is None


def test_locate_is_case_sensitive_because_quotes_must_be_exact() -> None:
    assert locate("total a pagar", "Total a pagar") is None


def test_source_text_maps_offsets_to_pages() -> None:
    source = SourceText(pages=("primera página", "segunda página"))
    assert source.text == "primera página\n\nsegunda página"
    assert source.page_at(0) == 1
    assert source.page_at(source.text.index("segunda")) == 2
