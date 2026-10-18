"""México: a CFDI 4.0 with its TimbreFiscalDigital (the SAT's stamp, through a PAC)."""

from __future__ import annotations

from xml.etree.ElementTree import Element

from custodio.extraction.einvoice.errors import NotAnEInvoice
from custodio.extraction.einvoice.model import EInvoice, Party, Standard, Term, XmlValue
from custodio.extraction.einvoice.xmlpath import Node, all_text

CFDI_NS = "http://www.sat.gob.mx/cfd/4"
OLD_CFDI_NS = "http://www.sat.gob.mx/cfd/3"
NAMESPACES = {"cfdi": CFDI_NS, "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital"}
ROOT_TAG = f"{{{CFDI_NS}}}Comprobante"
SUPPORTED_VERSION = "4.0"
INCOME = "I"  # TipoDeComprobante: ingreso, the only kind that asks to be paid
# SAT catalogue c_FormaPago, the forms a supplier invoice uses.
PAYMENT_FORMS = {
    "01": "efectivo",
    "02": "cheque nominativo",
    "03": "transferencia electrónica",
    "04": "tarjeta de crédito",
    "28": "tarjeta de débito",
    "99": "por definir",
}
ISO_DATE_LENGTH = len("2026-10-15")


def handles(root: Element) -> bool:
    return root.tag in (ROOT_TAG, f"{{{OLD_CFDI_NS}}}Comprobante")


def parse(root: Element) -> EInvoice:
    if root.tag != ROOT_TAG or root.get("Version") != SUPPORTED_VERSION:
        raise NotAnEInvoice(f"Custodio lee CFDI {SUPPORTED_VERSION}; este comprobante es de otra versión.")
    voucher = Node(root, "cfdi:Comprobante", NAMESPACES)
    if root.get("TipoDeComprobante") not in (None, INCOME):
        raise NotAnEInvoice("El CFDI no es de ingreso (TipoDeComprobante I): no es una factura por pagar.")
    concept = voucher.find("cfdi:Conceptos/cfdi:Concepto")
    stamp = voucher.find("cfdi:Complemento/tfd:TimbreFiscalDigital")
    return EInvoice(
        standard=Standard.CFDI,
        title="Comprobante fiscal digital por internet (CFDI 4.0, SAT)",
        authority="el SAT",
        unique_id_label="UUID (TimbreFiscalDigital)",
        unique_id=stamp.attribute("UUID") if stamp else None,
        number=_number(voucher),
        issue_date=_day(voucher.attribute("Fecha")),
        due_date=None,  # a CFDI states no due date; the agreement or a person does
        currency=voucher.attribute("Moneda"),
        exchange_rate=voucher.attribute("TipoCambio"),
        terms=_terms(voucher),
        total=voucher.attribute("Total"),
        payment_form=_payment_form(voucher),
        supplier=_party(voucher.find("cfdi:Emisor")),
        customer=_party(voucher.find("cfdi:Receptor")),
        bank_name=None,  # a CFDI never carries the supplier's bank account
        account=None,
        description=concept.attribute("Descripcion") if concept else None,
        notes=(),
        all_text=all_text(root),
    )


def _number(voucher: Node) -> XmlValue | None:
    serie, folio = voucher.attribute("Serie"), voucher.attribute("Folio")
    parts = [value for value in (serie, folio) if value]
    if not parts:
        return None
    path = " y ".join(value.path for value in parts)
    return XmlValue("-".join(value.text for value in parts), path)


def _day(stamp: XmlValue | None) -> XmlValue | None:
    return XmlValue(stamp.text[:ISO_DATE_LENGTH], stamp.path) if stamp else None


def _terms(voucher: Node) -> tuple[Term, ...]:
    """Total = SubTotal − Descuento + TotalImpuestosTrasladados − TotalImpuestosRetenidos (Anexo 20)."""
    taxes = voucher.find("cfdi:Impuestos")
    candidates = (
        ("subtotal", 1, voucher.attribute("SubTotal")),
        ("descuento", -1, voucher.attribute("Descuento")),
        ("impuestos trasladados", 1, taxes.attribute("TotalImpuestosTrasladados") if taxes else None),
        ("impuestos retenidos", -1, taxes.attribute("TotalImpuestosRetenidos") if taxes else None),
    )
    return tuple(Term(label, sign, value) for label, sign, value in candidates if value)


def _payment_form(voucher: Node) -> XmlValue | None:
    form = voucher.attribute("FormaPago")
    if form is None:
        return None
    meaning = PAYMENT_FORMS.get(form.text)
    method = voucher.attribute("MetodoPago")
    text = f"{form.text} ({meaning})" if meaning else form.text
    return XmlValue(f"{text}, método {method.text}" if method else text, form.path)


def _party(party: Node | None) -> Party:
    if party is None:
        return Party(name=None, tax_id=None)
    return Party(name=party.attribute("Nombre"), tax_id=party.attribute("Rfc"))
