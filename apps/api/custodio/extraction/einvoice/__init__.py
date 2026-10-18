"""Electronic invoices read by code: Colombia's DIAN UBL 2.1 and México's CFDI 4.0. No model reads them.

`read_einvoice` turns the official XML into an ExtractedInvoice whose every value cites its path in the XML, after
checks code can prove (CUFE or UUID form, NIT check digit or RFC form, totals, receiver). `merge` pairs it with a PDF
or image of the same invoice: the XML wins, and any disagreement stops the payment.
"""

from __future__ import annotations

import mimetypes

from custodio.extraction.einvoice.errors import NotAnEInvoice, UnsafeXml
from custodio.extraction.einvoice.pairing import is_einvoice_reading, merge, same_invoice
from custodio.extraction.einvoice.reading import read_einvoice
from custodio.extraction.einvoice.safe_xml import MAX_XML_BYTES

__all__ = [
    "MAX_XML_BYTES",
    "XML_MEDIA_TYPES",
    "NotAnEInvoice",
    "UnsafeXml",
    "is_einvoice",
    "is_einvoice_reading",
    "merge",
    "read_einvoice",
    "same_invoice",
]

XML_MEDIA_TYPES = frozenset({"application/xml", "text/xml"})
GENERIC_MEDIA_TYPES = frozenset({"", "application/octet-stream"})


def is_einvoice(media_type: str, filename: str) -> bool:
    """Whether an upload is an XML, by its declared type or, when the type says nothing, by its name."""
    declared = media_type.split(";")[0].strip().lower()
    if declared in GENERIC_MEDIA_TYPES:
        declared = mimetypes.guess_type(filename.lower())[0] or ""
    return declared in XML_MEDIA_TYPES
