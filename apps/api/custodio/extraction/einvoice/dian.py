"""Colombia: a DIAN electronic sales invoice (UBL 2.1), alone or inside the AttachedDocument the DIAN hands back."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from xml.etree.ElementTree import Element

from custodio.extraction.einvoice import safe_xml
from custodio.extraction.einvoice.errors import NotAnEInvoice
from custodio.extraction.einvoice.model import EInvoice, Party, Standard, Term, XmlValue
from custodio.extraction.einvoice.xmlpath import Node, all_text

INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
ATTACHED_NS = "urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2"
NAMESPACES = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
INVOICE_TAG = f"{{{INVOICE_NS}}}Invoice"
ATTACHED_TAG = f"{{{ATTACHED_NS}}}AttachedDocument"
EMBEDDED_INVOICE = "cac:Attachment/cac:ExternalReference/cbc:Description"
NIT_SCHEME = "31"  # DIAN identification type 31: NIT
WRITTEN_CHECK_DIGIT = re.compile(r"-\s*\d$")  # a NIT's DV after a dash; other ids (an EIN, 88-4410273) keep theirs
PAYMENT_FORMS = {"1": "contado", "2": "crédito"}
PARTY_NAMES = (
    "cac:PartyTaxScheme/cbc:RegistrationName",
    "cac:PartyLegalEntity/cbc:RegistrationName",
    "cac:PartyName/cbc:Name",
)
MONETARY = "cac:LegalMonetaryTotal"
OPTIONAL_TERMS = (
    ("AllowanceTotalAmount", "descuentos", -1),
    ("ChargeTotalAmount", "cargos", 1),
    ("PrepaidAmount", "anticipos", -1),
    ("PayableRoundingAmount", "redondeo", 1),
)


def handles(root: Element) -> bool:
    return root.tag in (INVOICE_TAG, ATTACHED_TAG)


def parse(root: Element) -> EInvoice:
    if root.tag == ATTACHED_TAG:
        return _parse_attached(Node(root, "AttachedDocument", NAMESPACES))
    return _parse_invoice(Node(root, "Invoice", NAMESPACES), extra_text="")


def _parse_attached(attached: Node) -> EInvoice:
    """The invoice travels as text inside the container; it goes through the same safe parser as any upload."""
    embedded = attached.text(EMBEDDED_INVOICE)
    if embedded is None or "Invoice" not in embedded.text:
        raise NotAnEInvoice("El AttachedDocument no trae una factura electrónica embebida.")
    inner = safe_xml.parse(embedded.text.encode())
    if inner.tag != INVOICE_TAG:
        raise NotAnEInvoice("El documento embebido en el AttachedDocument no es una factura (Invoice).")
    return _parse_invoice(Node(inner, f"{embedded.path} ▸ Invoice", NAMESPACES), extra_text=all_text(attached.element))


def _parse_invoice(invoice: Node, *, extra_text: str) -> EInvoice:
    means = invoice.find("cac:PaymentMeans")
    account = means.find("cac:PayeeFinancialAccount") if means else None
    return EInvoice(
        standard=Standard.DIAN,
        title="Factura electrónica de venta (DIAN, UBL 2.1)",
        authority="la DIAN",
        unique_id_label="CUFE",
        unique_id=invoice.text("cbc:UUID"),
        number=invoice.text("cbc:ID"),
        issue_date=invoice.text("cbc:IssueDate"),
        due_date=invoice.text("cbc:DueDate") or (means.text("cbc:PaymentDueDate") if means else None),
        currency=invoice.text("cbc:DocumentCurrencyCode"),
        exchange_rate=invoice.text("cac:PaymentExchangeRate/cbc:CalculationRate"),
        terms=_terms(invoice),
        total=invoice.text(f"{MONETARY}/cbc:PayableAmount"),
        payment_form=_payment_form(means),
        supplier=_party(invoice.find("cac:AccountingSupplierParty/cac:Party")),
        customer=_party(invoice.find("cac:AccountingCustomerParty/cac:Party")),
        bank_name=account.text("cac:FinancialInstitutionBranch/cbc:Name") if account else None,
        account=account.text("cbc:ID") if account else None,
        description=invoice.text("cac:InvoiceLine/cac:Item/cbc:Description"),
        notes=tuple(note.text for node in invoice.find_all("cbc:Note") if (note := node.own_text())),
        all_text="\n".join(filter(None, (extra_text, all_text(invoice.element)))),
    )


def _terms(invoice: Node) -> tuple[Term, ...]:
    """PayableAmount = LineExtensionAmount + taxes − allowances + charges − prepaid + rounding (DIAN, anexo 1.9)."""
    terms: list[Term] = []
    if subtotal := invoice.text(f"{MONETARY}/cbc:LineExtensionAmount"):
        terms.append(Term("subtotal", 1, subtotal))
    if taxes := _taxes(invoice):
        terms.append(Term("impuestos", 1, taxes))
    for element, label, sign in OPTIONAL_TERMS:
        if value := invoice.text(f"{MONETARY}/cbc:{element}"):
            terms.append(Term(label, sign, value))
    return tuple(terms)


def _taxes(invoice: Node) -> XmlValue | None:
    """The sum of the invoice-level TaxTotal amounts; withholdings (WithholdingTaxTotal) do not change the total."""
    amounts = [value for node in invoice.find_all("cac:TaxTotal/cbc:TaxAmount") if (value := node.own_text())]
    if not amounts:
        return None
    if len(amounts) == 1:
        return amounts[0]
    try:
        total = sum((Decimal(value.text) for value in amounts), Decimal(0))
    except InvalidOperation:
        return XmlValue(" + ".join(value.text for value in amounts), amounts[0].path)
    return XmlValue(str(total), f"{amounts[0].path} (suma de {len(amounts)})")


def _payment_form(means: Node | None) -> XmlValue | None:
    form = means.text("cbc:ID") if means else None
    if form is None:
        return None
    meaning = PAYMENT_FORMS.get(form.text)
    return XmlValue(f"{form.text} ({meaning})" if meaning else form.text, form.path)


def _party(party: Node | None) -> Party:
    if party is None:
        return Party(name=None, tax_id=None)
    name = next((value for path in PARTY_NAMES if (value := party.text(path))), None)
    company_id = party.find("cac:PartyTaxScheme/cbc:CompanyID") or party.find("cac:PartyLegalEntity/cbc:CompanyID")
    if company_id is None:
        return Party(name=name, tax_id=None)
    written, check_digit = company_id.own_text(), company_id.element.get("schemeID")
    is_nit = company_id.element.get("schemeName") == NIT_SCHEME
    if written and check_digit:
        written = XmlValue(written.text, f"{written.path} y @schemeID (DV)")
    elif written and is_nit and WRITTEN_CHECK_DIGIT.search(written.text):  # some write it: «901.223.610-9»
        number, _, check_digit = written.text.rpartition("-")
        written = XmlValue(number, written.path)
    return Party(name=name, tax_id=written, check_digit=check_digit, is_nit=is_nit)
