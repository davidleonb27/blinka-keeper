"""Fictitious electronic invoices addressed to the demo company: DIAN UBL 2.1 (Colombia) and CFDI 4.0 (México).

Every name, tax id, CUFE and UUID here is made up. The CUFE is a SHA-384 of the invoice's own fields with a made-up
technical key, so it has the DIAN's form but no DIAN ever issued it; the CFDI has no seal and no real stamp.

Run `uv run python -m custodio.dataset.einvoices` to write the demo files (see `DEMO_FILES`).
"""

from __future__ import annotations

import hashlib
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

DEMO_CUSTOMER = "Cobalto Labs, Inc."
DEMO_CUSTOMER_TAX_ID = "88-4410273"  # fictitious US EIN, written as a foreign id on Colombian and Mexican invoices
FICTITIOUS_TECHNICAL_KEY = "clave-tecnica-ficticia-custodio"
CFDI_UUID_NAMESPACE = uuid.UUID("6f1e0d4c-6a43-4b8e-9c0e-2f7b1a9d5c31")
FOREIGN_RFC = "XEXX010101000"  # the SAT's generic RFC for a foreign customer
UBL_NAMESPACES = (
    'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
    'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
)
ATTACHED_NAMESPACES = (
    'xmlns="urn:oasis:names:specification:ubl:schema:xsd:AttachedDocument-2" '
    'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
)
CENTS = Decimal("0.01")


@dataclass(frozen=True)
class DianSpec:
    number: str
    issue_date: date
    due_date: date | None
    supplier_name: str
    supplier_nit: str  # digits only, without the check digit
    supplier_dv: str  # the check digit as written on the invoice (may be wrong, on purpose)
    customer_name: str
    customer_id: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    description: str
    bank_name: str | None = None
    account: str | None = None
    currency: str = "COP"
    customer_scheme: str = "50"  # DIAN document type: 31 = NIT, 50 = foreign tax id
    notes: tuple[str, ...] = ()
    cufe: str | None = None  # None computes one; "" leaves the element out


@dataclass(frozen=True)
class CfdiSpec:
    serie: str
    folio: str
    issued_at: str  # YYYY-MM-DDThh:mm:ss
    supplier_name: str
    supplier_rfc: str
    customer_name: str
    customer_rfc: str
    subtotal: Decimal
    transferred: Decimal
    withheld: Decimal
    total: Decimal
    description: str
    currency: str = "MXN"
    exchange_rate: Decimal | None = None
    payment_form: str = "03"  # SAT catalogue: 03 = transferencia electrónica
    stamp_uuid: str | None = None  # None computes one; "" leaves the stamp out
    concepts: tuple[str, ...] = field(default=())


def dian_invoice(spec: DianSpec) -> str:
    cufe = _cufe(spec) if spec.cufe is None else spec.cufe
    due = f"<cbc:DueDate>{spec.due_date.isoformat()}</cbc:DueDate>" if spec.due_date else ""
    notes = "".join(f"<cbc:Note>{escape(note)}</cbc:Note>" for note in spec.notes)
    uuid_element = f'<cbc:UUID schemeName="CUFE-SHA384">{cufe}</cbc:UUID>' if cufe else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n<Invoice {UBL_NAMESPACES}>'
        "<cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID><cbc:CustomizationID>10</cbc:CustomizationID>"
        "<cbc:ProfileID>DIAN 2.1: Factura Electrónica de Venta</cbc:ProfileID>"
        f"<cbc:ID>{escape(spec.number)}</cbc:ID>{uuid_element}"
        f"<cbc:IssueDate>{spec.issue_date.isoformat()}</cbc:IssueDate><cbc:IssueTime>09:30:00-05:00</cbc:IssueTime>"
        f"{due}<cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>{notes}"
        f"<cbc:DocumentCurrencyCode>{spec.currency}</cbc:DocumentCurrencyCode>"
        f"{_ubl_party('AccountingSupplierParty', spec.supplier_name, spec.supplier_nit, spec.supplier_dv, '31')}"
        f"{_ubl_party('AccountingCustomerParty', spec.customer_name, spec.customer_id, None, spec.customer_scheme)}"
        f"{_payment_means(spec)}"
        f"<cac:TaxTotal><cbc:TaxAmount currencyID={quoteattr(spec.currency)}>{spec.tax}</cbc:TaxAmount>"
        "<cac:TaxSubtotal><cac:TaxCategory><cbc:Percent>19.00</cbc:Percent><cac:TaxScheme><cbc:ID>01</cbc:ID>"
        "<cbc:Name>IVA</cbc:Name></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>"
        f"<cac:LegalMonetaryTotal>{_money('LineExtensionAmount', spec.subtotal, spec.currency)}"
        f"{_money('TaxExclusiveAmount', spec.subtotal, spec.currency)}"
        f"{_money('TaxInclusiveAmount', spec.subtotal + spec.tax, spec.currency)}"
        f"{_money('PayableAmount', spec.total, spec.currency)}</cac:LegalMonetaryTotal>"
        f"<cac:InvoiceLine><cbc:ID>1</cbc:ID>{_money('LineExtensionAmount', spec.subtotal, spec.currency)}"
        f"<cac:Item><cbc:Description>{escape(spec.description)}</cbc:Description></cac:Item></cac:InvoiceLine>"
        "</Invoice>"
    )


def attached_document(invoice_xml: str, *, number: str) -> str:
    """The container the DIAN's validation returns: the invoice travels inside, as text, in a CDATA section."""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n<AttachedDocument {ATTACHED_NAMESPACES}>'
        "<cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID><cbc:ProfileID>Factura Electrónica de Venta</cbc:ProfileID>"
        f"<cbc:ParentDocumentID>{escape(number)}</cbc:ParentDocumentID>"
        "<cac:Attachment><cac:ExternalReference><cbc:MimeCode>text/xml</cbc:MimeCode>"
        f"<cbc:Description><![CDATA[{invoice_xml}]]></cbc:Description>"
        "</cac:ExternalReference></cac:Attachment></AttachedDocument>"
    )


def cfdi(spec: CfdiSpec) -> str:
    stamp_uuid = _stamp_uuid(spec) if spec.stamp_uuid is None else spec.stamp_uuid
    rate = f" TipoCambio={quoteattr(str(spec.exchange_rate))}" if spec.exchange_rate is not None else ""
    concepts = "".join(
        f'<cfdi:Concepto ClaveProdServ="81111500" Cantidad="1" ClaveUnidad="E48" Descripcion={quoteattr(text)} '
        f'ValorUnitario="{spec.subtotal}" Importe="{spec.subtotal}" ObjetoImp="02"/>'
        for text in (spec.description, *spec.concepts)
    )
    stamp = (
        '<cfdi:Complemento><tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital" '
        f'Version="1.1" UUID="{stamp_uuid}" FechaTimbrado="{spec.issued_at}" RfcProvCertif="SPR190613I52" '
        'NoCertificadoSAT="00001000000000000000"/></cfdi:Complemento>'
        if stamp_uuid
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0" '
        f"Serie={quoteattr(spec.serie)} Folio={quoteattr(spec.folio)} Fecha={quoteattr(spec.issued_at)} "
        f'FormaPago="{spec.payment_form}" MetodoPago="PUE" SubTotal="{spec.subtotal}" Moneda="{spec.currency}"{rate} '
        f'Total="{spec.total}" TipoDeComprobante="I" Exportacion="02" LugarExpedicion="06600">'
        f"<cfdi:Emisor Rfc={quoteattr(spec.supplier_rfc)} Nombre={quoteattr(spec.supplier_name)} "
        'RegimenFiscal="601"/>'
        f"<cfdi:Receptor Rfc={quoteattr(spec.customer_rfc)} Nombre={quoteattr(spec.customer_name)} "
        f'ResidenciaFiscal="USA" NumRegIdTrib="{DEMO_CUSTOMER_TAX_ID}" DomicilioFiscalReceptor="06600" '
        'RegimenFiscalReceptor="616" UsoCFDI="S01"/>'
        f"<cfdi:Conceptos>{concepts}</cfdi:Conceptos>"
        f'<cfdi:Impuestos TotalImpuestosTrasladados="{spec.transferred}" '
        f'TotalImpuestosRetenidos="{spec.withheld}"/>'
        f"{stamp}</cfdi:Comprobante>"
    )


def _ubl_party(role: str, name: str, tax_id: str, check_digit: str | None, scheme: str) -> str:
    dv = f' schemeID="{check_digit}"' if check_digit is not None else ""
    return (
        f"<cac:{role}><cac:Party><cac:PartyTaxScheme><cbc:RegistrationName>{escape(name)}</cbc:RegistrationName>"
        f'<cbc:CompanyID schemeAgencyID="195"{dv} schemeName="{scheme}">{escape(tax_id)}</cbc:CompanyID>'
        "<cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme></cac:PartyTaxScheme>"
        f"</cac:Party></cac:{role}>"
    )


def _payment_means(spec: DianSpec) -> str:
    account = ""
    if spec.account:
        bank = (
            f"<cac:FinancialInstitutionBranch><cbc:Name>{escape(spec.bank_name)}</cbc:Name>"
            "</cac:FinancialInstitutionBranch>"
            if spec.bank_name
            else ""
        )
        account = (
            f"<cac:PayeeFinancialAccount><cbc:ID>{escape(spec.account)}</cbc:ID>{bank}</cac:PayeeFinancialAccount>"
        )
    due = f"<cbc:PaymentDueDate>{spec.due_date.isoformat()}</cbc:PaymentDueDate>" if spec.due_date else ""
    return (
        "<cac:PaymentMeans><cbc:ID>2</cbc:ID><cbc:PaymentMeansCode>47</cbc:PaymentMeansCode>"
        f"{due}{account}</cac:PaymentMeans>"
    )


def _money(name: str, amount: Decimal, currency: str) -> str:
    return f'<cbc:{name} currencyID="{currency}">{amount.quantize(CENTS)}</cbc:{name}>'


def _cufe(spec: DianSpec) -> str:
    """The DIAN's CUFE recipe with a fictitious technical key: right form, never issued by the DIAN."""
    parts = (
        spec.number,
        spec.issue_date.isoformat(),
        "09:30:00-05:00",
        str(spec.subtotal),
        "01",
        str(spec.tax),
        str(spec.total),
        spec.supplier_nit,
        spec.customer_id,
        FICTITIOUS_TECHNICAL_KEY,
        "2",
    )
    return hashlib.sha384("".join(parts).encode()).hexdigest()


def _stamp_uuid(spec: CfdiSpec) -> str:
    return str(uuid.uuid5(CFDI_UUID_NAMESPACE, f"{spec.supplier_rfc}{spec.serie}{spec.folio}")).upper()


# Demo files -------------------------------------------------------------------------------------------------------

VALID_DIAN = DianSpec(
    number="DNC-1042",
    issue_date=date(2026, 10, 15),
    due_date=date(2026, 10, 30),
    supplier_name="Distrito Norte Coworking SAS",
    supplier_nit="901223610",
    supplier_dv="9",
    customer_name=DEMO_CUSTOMER,
    customer_id=DEMO_CUSTOMER_TAX_ID,
    subtotal=Decimal("3193277.31"),
    tax=Decimal("606722.69"),
    total=Decimal("3800000.00"),
    description="Coworking en Bogotá, octubre 2026",
    bank_name="Davivienda",
    account="0570-4410",
)
WRONG_CHECK_DIGIT_DIAN = DianSpec(
    number="EL-0388",
    issue_date=date(2026, 10, 15),
    due_date=date(2026, 10, 30),
    supplier_name="Estudio Lumbre SAS",
    supplier_nit="901552903",
    supplier_dv="7",  # the right one is 2
    customer_name=DEMO_CUSTOMER,
    customer_id=DEMO_CUSTOMER_TAX_ID,
    subtotal=Decimal("2605042.02"),
    tax=Decimal("494957.98"),
    total=Decimal("3100000.00"),
    description="Fotografía de producto, octubre 2026",
    bank_name="Bancolombia",
    account="0612-7731",
)
DEMO_CFDI = CfdiSpec(
    serie="CA",
    folio="2210",
    issued_at="2026-10-15T10:12:00",
    supplier_name="COLIBRI ANALITICA",
    supplier_rfc="CAN200815MX3",
    customer_name=DEMO_CUSTOMER.upper(),
    customer_rfc=FOREIGN_RFC,
    subtotal=Decimal("46000.00"),
    transferred=Decimal("0.00"),  # export of services: VAT at 0 %
    withheld=Decimal("0.00"),
    total=Decimal("46000.00"),
    description="Tableros de datos, octubre 2026",
)
DEMO_FILES: dict[str, str] = {
    "dian-distrito-norte-valida.xml": attached_document(dian_invoice(VALID_DIAN), number=VALID_DIAN.number),
    "dian-estudio-lumbre-nit-invalido.xml": dian_invoice(WRONG_CHECK_DIGIT_DIAN),
    "cfdi-colibri-analitica.xml": cfdi(DEMO_CFDI),
}
DEMO_DIRECTORY = Path(__file__).parent / "einvoices"


def write_demo_files(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in DEMO_FILES.items():
        path = directory / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    targets = [Path(arg) for arg in sys.argv[1:]] or [DEMO_DIRECTORY]
    for target in targets:
        for path in write_demo_files(target):
            print(path)
