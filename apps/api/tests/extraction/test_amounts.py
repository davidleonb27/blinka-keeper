from decimal import Decimal

import pytest

from custodio.extraction.amounts import amounts_in, currencies_named, format_amount, has_bare_dollar, parse_amount
from custodio.extraction.errors import AmountFormatError

PARSE_CASES = [
    # Latin: dot groups thousands, comma marks decimals
    ("4.200.000", "4200000"),
    ("4.200.000,00", "4200000.00"),
    ("1.234,5", "1234.5"),
    ("12,50", "12.50"),
    ("R$ 1.234,56", "1234.56"),
    ("COP 4.200.000", "4200000"),
    # Anglo: comma groups thousands, dot marks decimals
    ("4,200,000.00", "4200000.00"),
    ("USD 12,500.00", "12500.00"),
    ("12.50", "12.50"),
    ("1,234", "1234"),
    # a single separator followed by exactly three digits groups thousands
    ("$ 1.000", "1000"),
    ("1.000", "1000"),
    # ...unless the integer part is zero
    ("0,125", "0.125"),
    # no separators, apostrophes and narrow spaces as thousands
    ("12500", "12500"),
    ("1'234.50", "1234.50"),
    ("4 200 000,00", "4200000.00"),
    ("Total a pagar: $ 980,00", "980.00"),
]


@pytest.mark.parametrize(("text", "expected"), PARSE_CASES)
def test_parse_amount_reads_latin_and_anglo_formats(text: str, expected: str) -> None:
    assert parse_amount(text) == Decimal(expected)


@pytest.mark.parametrize(
    "text",
    [
        "1.2.3",  # groups of one digit
        "12,34,567",  # a two-digit group
        "1,234.567,89",  # the decimal mark appears twice
        "abc",  # no number at all
        "1.000 y 2.000",  # two amounts, which one?
        "",
    ],
)
def test_parse_amount_rejects_what_it_cannot_read_for_sure(text: str) -> None:
    with pytest.raises(AmountFormatError):
        parse_amount(text)


def test_amounts_in_finds_every_readable_amount_in_a_quote() -> None:
    quote = "Subtotal COP 4.000.000,00 · IVA 200.000,00 · Total 4.200.000,00"
    assert amounts_in(quote) == [Decimal("4000000.00"), Decimal("200000.00"), Decimal("4200000.00")]


def test_amounts_in_skips_number_like_text_it_cannot_read() -> None:
    assert amounts_in("Ref 1.2.3 por 1.500,00") == [Decimal("1500.00")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Total USD 12,500.00", {"USD"}),
        ("Valor: US$ 300", {"USD"}),
        ("R$ 1.234,56", {"BRL"}),
        ("COP 4.200.000", {"COP"}),
        ("cuatro millones de pesos colombianos", {"COP"}),
        ("MXN 15,000.00 (quince mil pesos mexicanos)", {"MXN"}),
        ("CLP 1.250.000", {"CLP"}),
        ("€ 90,00", {"EUR"}),
        ("$ 4.200.000", set()),
        ("Copia de la factura", set()),  # "COP" inside a word is not a currency
    ],
)
def test_currencies_named_needs_an_explicit_marker(text: str, expected: set[str]) -> None:
    assert currencies_named(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [("$ 4.200.000", True), ("Total: $980", True), ("US$ 300", False), ("R$ 10", False), ("COL$ 10", False)],
)
def test_has_bare_dollar_spots_the_ambiguous_sign(text: str, expected: bool) -> None:
    assert has_bare_dollar(text) is expected


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("4200000", "COP", "COP 4.200.000,00"),
        ("12500.5", "USD", "USD 12,500.50"),
        ("1250000", "CLP", "CLP 1.250.000"),
        ("15000", "MXN", "MXN 15,000.00"),
        ("1234.56", "BRL", "BRL 1.234,56"),
    ],
)
def test_format_amount_writes_each_currency_the_way_its_invoices_do(amount: str, currency: str, expected: str) -> None:
    assert format_amount(Decimal(amount), currency) == expected


@pytest.mark.parametrize(("amount", "currency"), [("4200000", "COP"), ("12500.5", "USD"), ("1250000", "CLP")])
def test_formatted_amounts_parse_back_to_the_same_number(amount: str, currency: str) -> None:
    assert parse_amount(format_amount(Decimal(amount), currency)) == Decimal(amount)
