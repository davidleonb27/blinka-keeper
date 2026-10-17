"""Bank statements exported as CSV: columns, separators, amounts and dates are detected by code, never guessed."""

from datetime import date
from decimal import Decimal

import pytest

from custodio.reconciliation.csv_statement import read_csv_statement
from custodio.reconciliation.errors import StatementFormatError
from custodio.reconciliation.models import Statement


def read(text: str, *, encoding: str = "utf-8", default_currency: str = "USD") -> Statement:
    return read_csv_statement(text.encode(encoding), default_currency=default_currency)


def test_spanish_headers_with_semicolons_and_latin_amounts() -> None:
    statement = read(
        "Fecha;Descripción;Monto;Moneda;Referencia\n"
        "16/10/2026;PAGO KT-0921 KORA TRADUCCIONES;-1.634,02;USD;KT-0921\n"
        "17/10/2026;ABONO CLIENTE NORTHWIND;18.500,00;USD;\n"
    )

    first, second = statement.movements
    assert first.booked_on == date(2026, 10, 16)
    assert first.description == "PAGO KT-0921 KORA TRADUCCIONES"
    assert first.amount == Decimal("-1634.02")
    assert first.currency == "USD"
    assert first.reference == "KT-0921"
    assert first.read is True
    assert second.amount == Decimal("18500.00")
    assert second.reference is None
    assert statement.reader == "csv"


def test_english_headers_with_commas_and_quoted_anglo_amounts() -> None:
    statement = read(
        "Date,Description,Amount,Currency,Reference\n"
        '2026-10-16,"Payment, Cumulus Hosting","-1,400.00",USD,CH-2026-1003\n'
    )

    (movement,) = statement.movements
    assert movement.description == "Payment, Cumulus Hosting"
    assert movement.amount == Decimal("-1400.00")
    assert movement.booked_on == date(2026, 10, 16)


def test_separate_debit_and_credit_columns_carry_the_sign() -> None:
    statement = read(
        "Fecha;Concepto;Cargo;Abono\n"
        "16/10/2026;TRANSFERENCIA DIEGO SALAZAR;1.600,00;\n"
        "16/10/2026;ABONO CLIENTE;;2.000,00\n"
    )

    assert [movement.amount for movement in statement.movements] == [Decimal("-1600.00"), Decimal("2000.00")]


def test_negative_amounts_in_parentheses_or_with_a_trailing_minus() -> None:
    statement = read(
        "Date;Description;Amount\n16/10/2026;Fee;(25.00)\n16/10/2026;Wire;1,400.00-\n16/10/2026;Wire;−12.50\n"
    )

    assert [movement.amount for movement in statement.movements] == [
        Decimal("-25.00"),
        Decimal("-1400.00"),
        Decimal("-12.50"),
    ]


def test_without_a_currency_column_the_account_currency_applies() -> None:
    statement = read("Fecha;Detalle;Valor\n16/10/2026;PAGO;-10,00\n", default_currency="COP")

    assert statement.movements[0].currency == "COP"


def test_the_preamble_before_the_header_and_balance_rows_are_skipped() -> None:
    statement = read(
        "Banco Andino - Extracto de cuenta corriente\n"
        "Cuenta;****4417\n"
        "\n"
        "Fecha;Descripción;Monto\n"
        "01/10/2026;Saldo inicial;94.500,00\n"
        "16/10/2026;PAGO PS-88412 PULSO SOFTWARE;-840,00\n"
        "31/10/2026;Saldo final;93.660,00\n"
    )

    assert [movement.description for movement in statement.movements] == ["PAGO PS-88412 PULSO SOFTWARE"]
    assert statement.movements[0].row == 6


def test_a_row_whose_amount_cannot_be_read_stays_unread_with_its_text() -> None:
    statement = read("Fecha;Descripción;Monto\n16/10/2026;PAGO RARO;mil doscientos\n")

    (movement,) = statement.movements
    assert movement.read is False
    assert movement.amount is None
    assert movement.quote == "16/10/2026;PAGO RARO;mil doscientos"
    assert movement.unread_reason is not None
    assert "monto" in movement.unread_reason


def test_a_row_whose_date_cannot_be_read_stays_unread() -> None:
    statement = read("Fecha;Descripción;Monto\n31/02/2026;PAGO;-10,00\n")

    (movement,) = statement.movements
    assert movement.read is False
    assert movement.booked_on is None
    assert movement.unread_reason is not None
    assert "fecha" in movement.unread_reason


def test_month_first_dates_are_detected_when_a_second_part_exceeds_twelve() -> None:
    statement = read("Date,Description,Amount\n10/16/2026,Wire,-10.00\n10/05/2026,Wire,-11.00\n")

    assert [movement.booked_on for movement in statement.movements] == [date(2026, 10, 16), date(2026, 10, 5)]


def test_ambiguous_numeric_dates_are_read_day_first_and_say_so() -> None:
    statement = read("Fecha;Descripción;Monto\n05/10/2026;PAGO;-10,00\n")

    assert statement.movements[0].booked_on == date(2026, 10, 5)
    assert any("día/mes" in warning for warning in statement.warnings)


def test_byte_order_mark_and_latin_1_files_are_decoded() -> None:
    with_bom = read("\ufeffFecha;Descripción;Monto\n16/10/2026;Comisión;-5,00\n")
    latin = read("Fecha;Descripción;Monto\n16/10/2026;Comisión;-5,00\n", encoding="latin-1")

    assert with_bom.movements[0].description == "Comisión"
    assert latin.movements[0].description == "Comisión"


def test_a_file_without_date_description_and_amount_columns_is_refused() -> None:
    with pytest.raises(StatementFormatError) as refused:
        read("Nombre;Ciudad\nAna;Bogotá\n")

    assert "fecha" in refused.value.message


def test_movement_ids_follow_the_file_order() -> None:
    statement = read("Fecha;Descripción;Monto\n16/10/2026;A;-1,00\n16/10/2026;B;-2,00\n")

    assert [movement.id for movement in statement.movements] == ["m001", "m002"]
