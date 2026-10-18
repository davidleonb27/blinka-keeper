"""What an electronic invoice says, each value with the path in the XML it was read from."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Standard(StrEnum):
    DIAN = "DIAN UBL 2.1"
    CFDI = "CFDI 4.0"


@dataclass(frozen=True)
class XmlValue:
    text: str
    path: str  # e.g. "Invoice/cac:LegalMonetaryTotal/cbc:PayableAmount" or "cfdi:Comprobante/@Total"


@dataclass(frozen=True)
class Party:
    name: XmlValue | None
    tax_id: XmlValue | None  # as written, without the check digit for a DIAN NIT
    check_digit: str | None = None  # the DIAN's DV, written apart in the schemeID attribute
    is_nit: bool = False


@dataclass(frozen=True)
class Term:
    """One addend of the invoice's arithmetic: the terms with their sign must add up to the total."""

    label: str  # Spanish, e.g. "impuestos"
    sign: int  # +1 or -1
    value: XmlValue


@dataclass(frozen=True)
class EInvoice:
    standard: Standard
    title: str  # Spanish, e.g. "Factura electrónica de venta (DIAN, UBL 2.1)"
    authority: str  # who could validate it online and was not asked: "la DIAN", "el SAT"
    unique_id_label: str  # "CUFE" or "UUID (TimbreFiscalDigital)"
    unique_id: XmlValue | None
    number: XmlValue | None
    issue_date: XmlValue | None
    due_date: XmlValue | None
    currency: XmlValue | None
    exchange_rate: XmlValue | None
    terms: tuple[Term, ...]
    total: XmlValue | None
    payment_form: XmlValue | None
    supplier: Party
    customer: Party
    bank_name: XmlValue | None
    account: XmlValue | None
    description: XmlValue | None
    notes: tuple[str, ...]
    all_text: str  # every text node and attribute value, scanned for instructions addressed to the agent
