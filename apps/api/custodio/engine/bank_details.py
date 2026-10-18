"""Is this account or tax id well formed for its rail? Check digits and forms published for each scheme (R13).

Pure functions, one per scheme. Each returns a `Check` whose `problem` is a Spanish clause with the concrete digits
(«la CLABE 0721… no pasa el dígito de control: esperado 7, viene 3»), or None when the value is valid. A valid
check digit proves the value was not mistyped; it never proves whose account it is (that is R4 and R15).

Bre-B alphanumeric keys («@kora2026») are not checked: the Banco de la República has not published a form for them
that code can verify, so only Bre-B keys by email, mobile number and NIT are recognized. Colombian, Brazilian and
Mexican bank account numbers outside CLABE have no public check digit and are not recognized either.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

ABA_WEIGHTS = (3, 7, 1)
ABA_DIGITS = 9
ACH_DIGITS = range(4, 18)
CLABE_WEIGHTS = (3, 7, 1)
CLABE_DIGITS = 18
CLABE_NEAR = range(17, 20)  # one digit short or long: still a CLABE, with a length problem
DIAN_WEIGHTS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)
NIT_DIGITS = range(5, len(DIAN_WEIGHTS) + 1)
CPF_DIGITS = 11
CNPJ_CHARS = 14
EIN = re.compile(r"\d{2}-?\d{7}")
RFC = re.compile(r"([A-ZÑ&]{3,4})(\d{6})([A-Z0-9]{3})")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")
EMAIL_MAX = 77  # Pix: the longest email key the Banco Central accepts
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
PIX_PHONE_DIGITS = (10, 11)  # area code (2) and number (8 or 9), after +55
BREB_MOBILE = re.compile(r"3\d{9}")
NIT_FORM = re.compile(r"[\d.\s]+-\s*\d")
ROUTING_LABEL = re.compile(r"(?i)\b(?:aba|routing|ruta)\b\D{0,12}?(\d{9})(?!\d)")
ROUTING_SLASH = re.compile(r"(\d{9})\s*/\s*([\d\s-]+)")
NUMBER_ONLY = re.compile(r"[\d\s.-]+")
MOD_97 = 97
# IBAN registry lengths: the countries of the demo company's suppliers that use IBAN, and the usual others.
IBAN_LENGTHS = {
    "AD": 24, "AE": 23, "AT": 20, "BE": 16, "BR": 29, "CH": 21, "CR": 22, "CY": 28, "CZ": 24, "DE": 22,
    "DK": 18, "DO": 28, "EE": 20, "ES": 24, "FI": 18, "FR": 27, "GB": 22, "GR": 27, "GT": 28, "HR": 21,
    "HU": 28, "IE": 22, "IL": 23, "IT": 27, "LT": 20, "LU": 20, "LV": 21, "MT": 31, "NL": 18, "NO": 15,
    "PL": 28, "PT": 25, "RO": 24, "SA": 24, "SE": 24, "SI": 19, "SK": 24, "SV": 28, "TR": 26,
}  # fmt: skip
IBAN_FORM = re.compile(r"([A-Z]{2})\d{2}[A-Z0-9]+")


@dataclass(frozen=True)
class Check:
    scheme: str  # Spanish name, e.g. "CLABE", "ruta ABA", "llave Pix (correo)"
    written: str  # as the document or the register wrote it
    problem: str | None = None  # Spanish clause with the concrete digits; None when valid

    @property
    def valid(self) -> bool:
        return self.problem is None


# United States -------------------------------------------------------------------------------------------------


def aba_routing(value: str) -> Check:
    digits = _digits(value)
    if len(digits) != ABA_DIGITS:
        return _wrong_length("ruta ABA", "la ruta ABA", value, len(digits), "9")
    total = sum(int(d) * ABA_WEIGHTS[i % 3] for i, d in enumerate(digits[:-1]))
    expected = str(-total % 10)
    if digits[-1] != expected:
        return _bad_digit(
            "ruta ABA", value, f"la ruta ABA {value} no pasa el dígito de control 3-7-1", expected, digits[-1]
        )
    return Check("ruta ABA", value)


def ach_account(value: str) -> Check:
    digits = _digits(value)
    if len(digits) not in ACH_DIGITS:
        return _wrong_length("cuenta ACH", "la cuenta ACH", value, len(digits), "de 4 a 17")
    return Check("cuenta ACH", value)


def ein(value: str) -> Check:
    if not EIN.fullmatch(value.strip()):
        return Check("EIN", value, f"el EIN {value} no tiene la forma de un EIN: 2 dígitos, guion opcional y 7 dígitos")
    return Check("EIN", value)


# Mexico --------------------------------------------------------------------------------------------------------


def clabe(value: str) -> Check:
    digits = _digits(value)
    if len(digits) != CLABE_DIGITS:
        return _wrong_length("CLABE", "la CLABE", value, len(digits), "18")
    total = sum(int(d) * CLABE_WEIGHTS[i % 3] % 10 for i, d in enumerate(digits[:-1]))
    expected = str(-total % 10)
    if digits[-1] != expected:
        return _bad_digit("CLABE", value, f"la CLABE {value} no pasa el dígito de control", expected, digits[-1])
    return Check("CLABE", value)


def rfc(value: str) -> Check:
    code = re.sub(r"[\s-]", "", value.upper())
    match = RFC.fullmatch(code)
    if match is None:
        return Check(
            "RFC",
            value,
            f"el RFC {value} no tiene la forma de un RFC: 3 o 4 letras, fecha AAMMDD y 3 caracteres de homoclave",
        )
    if not _real_yymmdd(match.group(2)):
        return Check("RFC", value, f"el RFC {value} trae una fecha que no existe ({match.group(2)})")
    return Check("RFC", value)


# Colombia ------------------------------------------------------------------------------------------------------


def nit(value: str) -> Check:
    number, _, written_digit = value.rpartition("-")
    digits = _digits(number) if number else _digits(value)[:-1]
    given = _digits(written_digit) if number else _digits(value)[-1:]
    if len(digits) not in NIT_DIGITS or len(given) != 1:
        return Check(
            "NIT",
            value,
            f"el NIT {value} tiene {len(digits)} dígitos antes del dígito de verificación; deben ser de 5 a 15",
        )
    expected = nit_check_digit(digits)
    if given != expected:
        return _bad_digit("NIT", value, f"el NIT {value} no pasa el dígito de verificación DIAN", expected, given)
    return Check("NIT", value)


def nit_check_digit(digits: str) -> str:
    """The DIAN's check digit (módulo 11) of a NIT written as digits only, without its own check digit."""
    remainder = sum(int(d) * w for d, w in zip(reversed(digits), DIAN_WEIGHTS, strict=False)) % 11
    return str(remainder if remainder < 2 else 11 - remainder)


def breb_key(value: str) -> Check | None:
    """A Bre-B key by email, Colombian mobile number or NIT; None for any other form (alphanumeric keys included)."""
    text = value.strip()
    if EMAIL.fullmatch(text):
        return Check("llave Bre-B (correo)", value)
    if text.startswith("+57"):
        digits = _digits(text[3:])
        if not BREB_MOBILE.fullmatch(digits):
            problem = f"la llave Bre-B {value} tiene {len(digits)} dígitos después de +57; deben ser 10 y empezar por 3"
            return Check("llave Bre-B (celular)", value, problem)
        return Check("llave Bre-B (celular)", value)
    if BREB_MOBILE.fullmatch(text.replace(" ", "")):
        return Check("llave Bre-B (celular)", value)
    if NIT_FORM.fullmatch(text):
        return _renamed(nit(value), "llave Bre-B (NIT)")
    return None


# Brazil --------------------------------------------------------------------------------------------------------


def cpf(value: str) -> Check:
    digits = _digits(value)
    if len(digits) != CPF_DIGITS:
        return _wrong_length("CPF", "el CPF", value, len(digits), "11")
    if len(set(digits)) == 1:
        return Check("CPF", value, f"el CPF {value} es una secuencia de un solo dígito repetido")
    values = [int(d) for d in digits]
    first = _cpf_digit(values[:9])
    expected = f"{first}{_cpf_digit([*values[:9], first])}"
    if digits[9:] != expected:
        return _bad_digit("CPF", value, f"el CPF {value} no pasa los dígitos verificadores", expected, digits[9:])
    return Check("CPF", value)


def cnpj(value: str) -> Check:
    """Numeric and, since July 2026, alphanumeric: each character counts as its code point minus 48."""
    code = re.sub(r"[^A-Z0-9]", "", value.upper())
    if len(code) != CNPJ_CHARS or not code[12:].isdigit():
        return _wrong_length("CNPJ", "el CNPJ", value, len(code), "14")
    if len(set(code)) == 1:
        return Check("CNPJ", value, f"el CNPJ {value} es una secuencia de un solo dígito repetido")
    values = [ord(char) - ord("0") for char in code]
    first = _cnpj_digit(values[:12])
    expected = f"{first}{_cnpj_digit([*values[:12], first])}"
    if code[12:] != expected:
        return _bad_digit("CNPJ", value, f"el CNPJ {value} no pasa los dígitos verificadores", expected, code[12:])
    return Check("CNPJ", value)


def pix_key(value: str) -> Check | None:
    """A Pix key: email, +55 phone, CPF, CNPJ or random key (EVP, a UUID); None for any other form."""
    text = value.strip()
    if EMAIL.fullmatch(text):
        problem = f"la llave Pix {value} tiene más de {EMAIL_MAX} caracteres" if len(text) > EMAIL_MAX else None
        return Check("llave Pix (correo)", value, problem)
    if UUID.fullmatch(text):
        return Check("llave Pix (aleatoria)", value)
    if text.startswith("+55"):
        digits = _digits(text[3:])
        if len(digits) not in PIX_PHONE_DIGITS:
            problem = f"la llave Pix {value} tiene {len(digits)} dígitos después de +55; deben ser 10 u 11"
            return Check("llave Pix (celular)", value, problem)
        return Check("llave Pix (celular)", value)
    if NUMBER_ONLY.fullmatch(text) or "/" in text:
        code = re.sub(r"[^A-Z0-9]", "", text.upper())
        if len(code) == CPF_DIGITS:
            return _renamed(cpf(value), "llave Pix (CPF)")
        if len(code) == CNPJ_CHARS:
            return _renamed(cnpj(value), "llave Pix (CNPJ)")
    return None


# IBAN ----------------------------------------------------------------------------------------------------------


def iban(value: str) -> Check:
    code = re.sub(r"[^A-Z0-9]", "", value.upper())
    country = code[:2]
    length = IBAN_LENGTHS.get(country)
    if length is None:
        return Check("IBAN", value, f"el IBAN {value} es de un país sin largo IBAN conocido ({country})")
    if len(code) != length:
        return Check("IBAN", value, f"el IBAN {value} tiene {len(code)} caracteres; en {country} deben ser {length}")
    expected = f"{MOD_97 + 1 - _mod_97(code[4:] + country + '00'):02d}"
    if _mod_97(code[4:] + code[:4]) != 1:
        problem = (
            f"el IBAN {value} no pasa la verificación mod 97: dígitos de control esperados {expected}, "
            f"vienen {code[2:4]}"
        )
        return Check("IBAN", value, problem)
    return Check("IBAN", value)


# Which scheme applies ------------------------------------------------------------------------------------------


def account_checks(value: str, *, currency: str | None, country: str | None) -> tuple[Check, ...]:
    """The checks an account follows on its rail; empty when no scheme with a public check is recognized.

    The currency picks the rail (MXN → SPEI, BRL → Pix, COP → Bre-B, USD → ACH inside the United States); an IBAN
    is recognized by its form in any currency.
    """
    code = re.sub(r"[^A-Z0-9]", "", value.upper())
    form = IBAN_FORM.fullmatch(code)
    if "@" not in value and form is not None and form.group(1) in IBAN_LENGTHS:
        return (iban(value),)
    rail = RAILS.get(currency or "")
    if rail is None or (currency == "USD" and country not in (None, "US")):
        return ()
    return rail(value)


def tax_id_check(value: str, *, country: str | None) -> Check | None:
    """NIT (CO), CPF or CNPJ (BR), RFC (MX) and EIN (US); None when the country has no scheme checked here."""
    if country == "CO":
        return nit(value) if NIT_FORM.fullmatch(value.strip()) else None
    if country == "BR":
        return cnpj(value) if len(re.sub(r"[^A-Z0-9]", "", value.upper())) == CNPJ_CHARS else cpf(value)
    if country == "MX":
        return rfc(value)
    if country == "US":
        return ein(value)
    return None


def _spei(value: str) -> tuple[Check, ...]:
    is_clabe = NUMBER_ONLY.fullmatch(value.strip()) is not None and len(_digits(value)) in CLABE_NEAR
    return (clabe(value),) if is_clabe else ()


def _pix(value: str) -> tuple[Check, ...]:
    key = pix_key(value)
    return (key,) if key else ()


def _breb(value: str) -> tuple[Check, ...]:
    key = breb_key(value)
    return (key,) if key else ()


def _ach(value: str) -> tuple[Check, ...]:
    labelled = ROUTING_LABEL.search(value)
    if labelled is not None:
        rest = value[: labelled.start(1)] + value[labelled.end(1) :]
        return (aba_routing(labelled.group(1)), ach_account(_digits(rest)))
    slashed = ROUTING_SLASH.fullmatch(value.strip())
    if slashed is not None:
        return (aba_routing(slashed.group(1)), ach_account(slashed.group(2).strip()))
    return (ach_account(value),) if NUMBER_ONLY.fullmatch(value.strip()) else ()


RAILS: dict[str, Callable[[str], tuple[Check, ...]]] = {"MXN": _spei, "BRL": _pix, "COP": _breb, "USD": _ach}


# Helpers -------------------------------------------------------------------------------------------------------


def _digits(text: str) -> str:
    return "".join(char for char in text if char.isdigit())


def _wrong_length(scheme: str, subject: str, value: str, count: int, wanted: str) -> Check:
    return Check(scheme, value, f"{subject} {value} tiene {count} dígitos; deben ser {wanted}")


def _bad_digit(scheme: str, value: str, clause: str, expected: str, given: str) -> Check:
    verbs = ("esperados", "vienen") if len(expected) > 1 else ("esperado", "viene")
    return Check(scheme, value, f"{clause}: {verbs[0]} {expected}, {verbs[1]} {given}")


def _renamed(check: Check, scheme: str) -> Check:
    return Check(scheme, check.written, check.problem)


def _real_yymmdd(text: str) -> bool:
    year, month, day = int(text[:2]), int(text[2:4]), int(text[4:])
    return any(_is_date(century + year, month, day) for century in (1900, 2000))


def _is_date(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _cpf_digit(values: list[int]) -> int:
    weight = len(values) + 1
    return sum(v * (weight - i) for i, v in enumerate(values)) * 10 % 11 % 10


def _cnpj_digit(values: list[int]) -> int:
    weights = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)[-len(values) :]
    remainder = sum(v * w for v, w in zip(values, weights, strict=True)) % 11
    return 0 if remainder < 2 else 11 - remainder


def _mod_97(code: str) -> int:
    return int("".join(str(int(char, 36)) for char in code)) % MOD_97
