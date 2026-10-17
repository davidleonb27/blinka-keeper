from decimal import Decimal

import pytest

from custodio.ai.numbers import amounts_in, parse_amount


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("12500", "12500"),
        ("3.000", "3000"),
        ("4.200.000", "4200000"),
        ("4.200.000,50", "4200000.50"),
        ("4,200,000.50", "4200000.50"),
        ("2,5", "2.5"),
        ("2.5", "2.5"),
        ("2,500", "2500"),
        ("0,9", "0.9"),
    ],
)
def test_parse_amount_reads_latin_and_anglo_formats(token: str, expected: str) -> None:
    assert parse_amount(token) == Decimal(expected)


@pytest.mark.parametrize("token", ["", "abc", "1.2.3,4,5", "1,,2", "."])
def test_parse_amount_rejects_what_is_not_a_number(token: str) -> None:
    assert parse_amount(token) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("nada sobre 3.000 dólares sin aprobación", "3000"),
        ("deja siempre 80 mil de colchón", "80000"),
        ("un tope de 1,5 millones", "1500000"),
        ("hasta 2 millones de pesos", "2000000"),
        ("hasta 10k al mes", "10000"),
        ("nada sobre tres mil dólares", "3000"),
        ("ochenta mil de reserva", "80000"),
        ("dos mil quinientos fijos", "2500"),
        ("un millón doscientos mil", "1200000"),
        ("cuarenta y cinco mil", "45000"),
        ("veintidós días", "22"),
    ],
)
def test_amounts_in_understands_spanish_ways_of_writing_money(text: str, expected: str) -> None:
    assert Decimal(expected) in amounts_in(text)


def test_amounts_in_reads_dates_and_rule_ids_as_their_parts() -> None:
    found = amounts_in("Factura del 2026-10-12, regla R9")
    assert {Decimal(2026), Decimal(10), Decimal(12), Decimal(9)} <= found


def test_amounts_in_ignores_text_without_numbers() -> None:
    assert amounts_in("no pagues en reales") == set()
