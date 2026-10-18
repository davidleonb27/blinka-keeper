"""What code can prove about an electronic invoice without asking anyone: form, arithmetic and who it is for.

Nothing here calls the DIAN or the SAT, and the digital signature is not verified; the acta says so. A failed check
names the field of the reading it makes untrustworthy, so R1 (or R13 for a tax id) stops the payment.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from custodio.engine.bank_details import nit_check_digit, rfc
from custodio.engine.text import normalize_name
from custodio.extraction.einvoice.model import EInvoice, Party, Standard, Term, XmlValue

CUFE = re.compile(r"[0-9a-fA-F]{96}")  # SHA-384 in hexadecimal
STAMP_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
TOTALS_TOLERANCE = Decimal("0.01")  # one cent, for rounding between line and invoice totals
LEGAL_ENTITY_RFC_LENGTH = 12  # persona moral; a persona física has 13
NIT_GROUP = 3
# Fields of the reading a failed check distrusts. A broken document as a whole distrusts what would be paid.
DOCUMENT_FIELD = "amount"
TAX_ID_FIELD = "supplier_tax_id"


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    line: str  # Spanish, one sentence for the acta
    field: str | None = None  # the reading's field it distrusts when it fails


def run_checks(invoice: EInvoice, company_name: str | None) -> list[CheckResult]:
    return [_unique_id(invoice), _supplier_tax_id(invoice), _totals(invoice), _receiver(invoice.customer, company_name)]


def nit_text(digits: str, check_digit: str | None) -> str:
    """«901223610» and «9» -> «901.223.610-9»: how a NIT is written in Colombia."""
    groups: list[str] = []
    while digits:
        digits, group = digits[:-NIT_GROUP], digits[-NIT_GROUP:]
        groups.insert(0, group)
    written = ".".join(groups)
    return f"{written}-{check_digit}" if check_digit else written


def _passed(line: str) -> CheckResult:
    return CheckResult(True, line)


def _failed(line: str, field: str) -> CheckResult:
    return CheckResult(False, line, field)


# CUFE / UUID ------------------------------------------------------------------------------------------------------


def _unique_id(invoice: EInvoice) -> CheckResult:
    if invoice.standard is Standard.DIAN:
        return _form_check(
            invoice,
            CUFE,
            missing="La factura no trae CUFE (cbc:UUID): sin él no es una factura electrónica de la DIAN.",
            good="El CUFE tiene la forma de la DIAN (96 caracteres hexadecimales, SHA-384).",
            wrong="no tiene la forma de la DIAN (96 caracteres hexadecimales)",
        )
    return _form_check(
        invoice,
        STAMP_UUID,
        missing="El CFDI no trae el UUID del TimbreFiscalDigital: no está timbrado.",
        good="El UUID del timbre fiscal tiene la forma del SAT (8-4-4-4-12 hexadecimal).",
        wrong="no tiene la forma de un UUID del SAT (8-4-4-4-12 hexadecimal)",
    )


def _form_check(invoice: EInvoice, form: re.Pattern[str], *, missing: str, good: str, wrong: str) -> CheckResult:
    found = invoice.unique_id
    if found is None:
        return _failed(missing, DOCUMENT_FIELD)
    if not form.fullmatch(found.text):
        label = invoice.unique_id_label.split()[0]
        return _failed(f"El {label} «{found.text}» {wrong}.", DOCUMENT_FIELD)
    return _passed(good)


# NIT / RFC --------------------------------------------------------------------------------------------------------


def _supplier_tax_id(invoice: EInvoice) -> CheckResult:
    tax_id = invoice.supplier.tax_id
    if tax_id is None:
        return _failed("La factura no trae la identificación fiscal del emisor.", TAX_ID_FIELD)
    check: Callable[[Party, XmlValue], CheckResult] = _nit if invoice.standard is Standard.DIAN else _rfc
    return check(invoice.supplier, tax_id)


def _nit(party: Party, tax_id: XmlValue) -> CheckResult:
    digits = re.sub(r"\D", "", tax_id.text)
    if not party.is_nit:
        return _passed(f"El emisor se identifica con {tax_id.text}, que no es un NIT: no hay dígito que comprobar.")
    written = nit_text(digits, party.check_digit)
    if not party.check_digit:
        return _failed(f"El NIT {written} no trae dígito de verificación (atributo schemeID).", TAX_ID_FIELD)
    expected = nit_check_digit(digits)
    if party.check_digit != expected:
        return _failed(
            f"El NIT {written} tiene un dígito de verificación inválido; el correcto es {expected}.", TAX_ID_FIELD
        )
    return _passed(f"El NIT {written} pasa el dígito de verificación de la DIAN (módulo 11).")


def _rfc(_: Party, tax_id: XmlValue) -> CheckResult:
    found = rfc(tax_id.text)
    if found.problem:
        return _failed(f"{found.problem[0].upper()}{found.problem[1:]}.", TAX_ID_FIELD)
    code = re.sub(r"[\s-]", "", tax_id.text)
    kind = "persona moral" if len(code) == LEGAL_ENTITY_RFC_LENGTH else "persona física"
    return _passed(f"El RFC {tax_id.text} tiene la forma de una {kind} ({len(code)} caracteres).")


# Totals -----------------------------------------------------------------------------------------------------------


def _totals(invoice: EInvoice) -> CheckResult:
    if invoice.total is None:
        return _failed("La factura no trae el total a pagar.", DOCUMENT_FIELD)
    try:
        total = _finite(invoice.total.text)
        addends = [(term, _finite(term.value.text)) for term in invoice.terms]
    except InvalidOperation:
        return _failed("Un monto del XML no es un número; no se puede comprobar el total.", DOCUMENT_FIELD)
    if not addends:
        return _failed("La factura no desglosa subtotal ni impuestos; no se puede comprobar el total.", DOCUMENT_FIELD)
    computed = sum((term.sign * amount for term, amount in addends), Decimal(0))
    sum_text = _sum_text(addends)
    if abs(computed - total) > TOTALS_TOLERANCE:
        return _failed(
            f"Los totales no cuadran: {sum_text} = {computed}, pero el total dice {invoice.total.text}.",
            DOCUMENT_FIELD,
        )
    return _passed(f"Los totales cuadran: {sum_text} = total {invoice.total.text}.")


def _finite(text: str) -> Decimal:
    """A Decimal that is a real amount: NaN and Infinity parse, but are not numbers an invoice can state."""
    amount = Decimal(text)
    if not amount.is_finite():
        raise InvalidOperation(text)
    return amount


def _sum_text(addends: list[tuple[Term, Decimal]]) -> str:
    first, *rest = addends
    pieces = [f"{first[0].label} {first[0].value.text}"]
    pieces += [f"{'+' if term.sign > 0 else '−'} {term.label} {term.value.text}" for term, _ in rest]
    return " ".join(pieces)


# Receiver ---------------------------------------------------------------------------------------------------------


def _receiver(customer: Party, company_name: str | None) -> CheckResult:
    if customer.name is None:
        return _failed("La factura no dice a quién se le factura (receptor).", DOCUMENT_FIELD)
    if company_name is None:
        return _passed("No se comprobó el receptor: este espacio no tiene el nombre de su empresa.")
    if normalize_name(customer.name.text) != normalize_name(company_name):
        return _failed(
            f"La factura es para «{customer.name.text}», no para «{company_name}»: no es una cuenta por pagar de "
            "esta empresa.",
            DOCUMENT_FIELD,
        )
    return _passed(f"El receptor «{customer.name.text}» es la empresa de este espacio.")
