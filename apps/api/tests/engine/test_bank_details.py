"""Known valid and invalid vectors for every bank detail and tax id the engine checks (R13)."""

import pytest

from custodio.engine.bank_details import (
    Check,
    aba_routing,
    account_checks,
    ach_account,
    breb_key,
    clabe,
    cnpj,
    cpf,
    ein,
    iban,
    nit,
    pix_key,
    rfc,
    tax_id_check,
)


def valid(check: Check | None) -> bool:
    assert check is not None
    return check.valid


def problem(check: Check | None) -> str:
    assert check is not None and check.problem is not None
    return check.problem


# ABA routing and ACH account (United States) -------------------------------------------------------------------


@pytest.mark.parametrize("routing", ["021000021", "011000015", "121000358", "0210 0002 1"])
def test_aba_routing_numbers_with_a_good_3_7_1_checksum_are_valid(routing: str) -> None:
    assert valid(aba_routing(routing))


def test_an_aba_routing_number_with_a_typo_says_which_digit_was_expected() -> None:
    assert problem(aba_routing("021000022")) == (
        "la ruta ABA 021000022 no pasa el dígito de control 3-7-1: esperado 1, viene 2"
    )


def test_an_aba_routing_number_must_have_nine_digits() -> None:
    assert problem(aba_routing("02100002")) == "la ruta ABA 02100002 tiene 8 dígitos; deben ser 9"


@pytest.mark.parametrize("account", ["1234", "0612-4821", "12345678901234567"])
def test_ach_accounts_have_4_to_17_digits(account: str) -> None:
    assert valid(ach_account(account))


@pytest.mark.parametrize(("account", "digits"), [("123", 3), ("123456789012345678", 18)])
def test_ach_accounts_outside_4_to_17_digits_are_invalid(account: str, digits: int) -> None:
    assert problem(ach_account(account)) == f"la cuenta ACH {account} tiene {digits} dígitos; deben ser de 4 a 17"


# CLABE (Mexico) ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["032180000118359719", "002010077777777771", "072 180 00123456789 7"])
def test_clabes_with_a_good_check_digit_are_valid(value: str) -> None:
    assert valid(clabe(value))


def test_a_clabe_with_a_typo_says_the_expected_and_the_written_check_digit() -> None:
    assert problem(clabe("072180001234567893")) == (
        "la CLABE 072180001234567893 no pasa el dígito de control: esperado 7, viene 3"
    )


def test_a_clabe_must_have_eighteen_digits() -> None:
    assert problem(clabe("07218000123456789")) == "la CLABE 07218000123456789 tiene 17 dígitos; deben ser 18"


# IBAN ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "DE89370400440532013000",
        "GB82 WEST 1234 5698 7654 32",
        "ES9121000418450200051332",
        "FR1420041010050500013M02606",
        "PT50000201231234567890154",
        "BR1800360305000010009795493C1",
    ],
)
def test_ibans_of_the_right_length_with_mod_97_equal_to_1_are_valid(value: str) -> None:
    assert valid(iban(value))


def test_an_iban_with_a_typo_names_the_expected_check_digits() -> None:
    assert problem(iban("DE88370400440532013000")) == (
        "el IBAN DE88370400440532013000 no pasa la verificación mod 97: dígitos de control esperados 89, vienen 88"
    )


def test_an_iban_must_have_its_country_length() -> None:
    assert problem(iban("DE89-3704-0044")) == "el IBAN DE89-3704-0044 tiene 12 caracteres; en DE deben ser 22"


def test_an_iban_of_a_country_without_a_known_length_is_not_checked_as_valid() -> None:
    assert problem(iban("ZZ12345678901234")) == "el IBAN ZZ12345678901234 es de un país sin largo IBAN conocido (ZZ)"


# NIT (Colombia) ------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["800.197.268-4", "901.482.337-2", "900418557-0", "8001972684"])
def test_nits_with_a_good_dian_check_digit_are_valid(value: str) -> None:
    assert valid(nit(value))


def test_a_nit_with_a_wrong_check_digit_names_the_expected_one() -> None:
    assert problem(nit("901.482.337-9")) == (
        "el NIT 901.482.337-9 no pasa el dígito de verificación DIAN: esperado 2, viene 9"
    )


def test_a_nit_must_have_a_number_and_a_check_digit() -> None:
    assert (
        problem(nit("1234-5")) == "el NIT 1234-5 tiene 4 dígitos antes del dígito de verificación; deben ser de 5 a 15"
    )


# CPF and CNPJ (Brazil) -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["529.982.247-25", "52998224725", "412.889.330-70"])
def test_cpfs_with_good_check_digits_are_valid(value: str) -> None:
    assert valid(cpf(value))


def test_a_cpf_with_wrong_check_digits_names_the_expected_ones() -> None:
    assert problem(cpf("529.982.247-24")) == (
        "el CPF 529.982.247-24 no pasa los dígitos verificadores: esperados 25, vienen 24"
    )


@pytest.mark.parametrize("value", ["111.111.111-11", "000.000.000-00"])
def test_a_cpf_made_of_one_repeated_digit_is_rejected(value: str) -> None:
    assert problem(cpf(value)) == f"el CPF {value} es una secuencia de un solo dígito repetido"


def test_a_cpf_must_have_eleven_digits() -> None:
    assert problem(cpf("529.982.247-2")) == "el CPF 529.982.247-2 tiene 10 dígitos; deben ser 11"


@pytest.mark.parametrize("value", ["11.222.333/0001-81", "41.552.870/0001-50", "12.ABC.345/01DE-35"])
def test_cnpjs_with_good_check_digits_are_valid_including_the_alphanumeric_ones(value: str) -> None:
    assert valid(cnpj(value))


def test_a_cnpj_with_wrong_check_digits_names_the_expected_ones() -> None:
    assert problem(cnpj("41.552.870/0001-06")) == (
        "el CNPJ 41.552.870/0001-06 no pasa los dígitos verificadores: esperados 50, vienen 06"
    )


def test_a_cnpj_made_of_one_repeated_digit_is_rejected() -> None:
    assert problem(cnpj("00.000.000/0000-00")) == (
        "el CNPJ 00.000.000/0000-00 es una secuencia de un solo dígito repetido"
    )


# RFC (Mexico) and EIN (United States), by form -----------------------------------------------------------------


@pytest.mark.parametrize("value", ["PNO190312KD4", "HESO900214QW1", "ABC-000229-XY1"])
def test_rfcs_of_companies_and_people_with_a_real_date_are_valid(value: str) -> None:
    assert valid(rfc(value))


def test_an_rfc_must_have_the_form_of_letters_date_and_homoclave() -> None:
    assert problem(rfc("PN0190312KD4")) == (
        "el RFC PN0190312KD4 no tiene la forma de un RFC: 3 o 4 letras, fecha AAMMDD y 3 caracteres de homoclave"
    )


def test_an_rfc_with_a_date_that_does_not_exist_is_invalid() -> None:
    assert problem(rfc("PNO191332KD4")) == "el RFC PNO191332KD4 trae una fecha que no existe (191332)"


@pytest.mark.parametrize("value", ["84-2219034", "842219034"])
def test_eins_of_two_and_seven_digits_are_valid(value: str) -> None:
    assert valid(ein(value))


def test_an_ein_must_have_two_and_seven_digits() -> None:
    assert problem(ein("842-219034")) == (
        "el EIN 842-219034 no tiene la forma de un EIN: 2 dígitos, guion opcional y 7 dígitos"
    )


# Pix and Bre-B keys --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "scheme"),
    [
        ("pagos@cajucloud.com.br", "llave Pix (correo)"),
        ("+5511987654321", "llave Pix (celular)"),
        ("529.982.247-25", "llave Pix (CPF)"),
        ("11222333000181", "llave Pix (CNPJ)"),
        ("123e4567-e89b-42d3-a456-426614174000", "llave Pix (aleatoria)"),
    ],
)
def test_pix_keys_of_every_kind_are_recognized_and_valid(value: str, scheme: str) -> None:
    key = pix_key(value)
    assert key is not None and key.scheme == scheme and key.valid


def test_a_pix_key_with_a_document_typo_is_invalid() -> None:
    assert problem(pix_key("529.982.247-24")).startswith("el CPF 529.982.247-24 no pasa")


def test_a_pix_phone_key_must_have_the_area_code_and_number() -> None:
    assert (
        problem(pix_key("+5511987654")) == "la llave Pix +5511987654 tiene 8 dígitos después de +55; deben ser 10 u 11"
    )


def test_a_bank_account_is_not_a_pix_key() -> None:
    assert pix_key("0341-5542") is None


@pytest.mark.parametrize(
    ("value", "scheme"),
    [
        ("pagos@koratraducciones.co", "llave Bre-B (correo)"),
        ("3001234567", "llave Bre-B (celular)"),
        ("+57 300 123 4567", "llave Bre-B (celular)"),
        ("901.482.337-2", "llave Bre-B (NIT)"),
    ],
)
def test_breb_keys_by_email_phone_and_document_are_recognized_and_valid(value: str, scheme: str) -> None:
    key = breb_key(value)
    assert key is not None and key.scheme == scheme and key.valid


def test_a_breb_phone_key_must_be_a_colombian_mobile_number() -> None:
    assert problem(breb_key("+57 300 123 456")) == (
        "la llave Bre-B +57 300 123 456 tiene 9 dígitos después de +57; deben ser 10 y empezar por 3"
    )


@pytest.mark.parametrize("value", ["@kora2026", "0010-1975"])
def test_alphanumeric_breb_keys_and_plain_accounts_are_not_recognized(value: str) -> None:
    assert breb_key(value) is None


# Which scheme an account follows, by currency and country ------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "currency", "country", "schemes"),
    [
        ("072180001234567897", "MXN", "MX", ["CLABE"]),
        ("0721800012345678", "MXN", "MX", []),  # 16 digits: a card, not a CLABE
        ("ABA 021000021 cuenta 12345678", "USD", "US", ["ruta ABA", "cuenta ACH"]),
        ("021000021 / 12345678", "USD", None, ["ruta ABA", "cuenta ACH"]),
        ("2214-1180", "USD", "US", ["cuenta ACH"]),
        ("0612-4821", "USD", "CO", []),  # a wire abroad: no public check digit
        ("DE89 3704 0044 0532 0130 00", "EUR", "DE", ["IBAN"]),
        ("pagos@cajucloud.com.br", "BRL", "BR", ["llave Pix (correo)"]),
        ("0341-5542", "BRL", "BR", []),
        ("3001234567", "COP", "CO", ["llave Bre-B (celular)"]),
        ("0570-4410", "COP", "CO", []),
        ("0127-7710", "MXN", "MX", []),
    ],
)
def test_the_scheme_comes_from_the_currency_the_country_and_the_form(
    value: str, currency: str, country: str | None, schemes: list[str]
) -> None:
    assert [check.scheme for check in account_checks(value, currency=currency, country=country)] == schemes


def test_a_clabe_one_digit_short_is_still_checked_as_a_clabe() -> None:
    [check] = account_checks("07218000123456789", currency="MXN", country="MX")
    assert check.scheme == "CLABE" and not check.valid


def test_a_routing_number_with_a_typo_is_reported_next_to_a_valid_account() -> None:
    routing, account = account_checks("ABA 021000022 cuenta 12345678", currency="USD", country="US")
    assert not routing.valid and account.valid


@pytest.mark.parametrize(
    ("value", "country", "scheme", "is_valid"),
    [
        ("901.482.337-2", "CO", "NIT", True),
        ("901.482.337-1", "CO", "NIT", False),
        ("412.889.330-70", "BR", "CPF", True),
        ("41.552.870/0001-06", "BR", "CNPJ", False),
        ("PNO190312KD4", "MX", "RFC", True),
        ("84-2219034", "US", "EIN", True),
    ],
)
def test_the_tax_id_scheme_comes_from_the_country(value: str, country: str, scheme: str, is_valid: bool) -> None:
    check = tax_id_check(value, country=country)
    assert check is not None and (check.scheme, check.valid) == (scheme, is_valid)


@pytest.mark.parametrize(
    ("value", "country"),
    [("1.020.334.118", "CO"), ("30-71644029-5", "AR"), ("901.482.337-1", None), ("77.341.908-2", "CL")],
)
def test_tax_ids_without_a_known_scheme_are_not_checked(value: str, country: str | None) -> None:
    assert tax_id_check(value, country=country) is None
