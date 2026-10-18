"""The only way an XML enters Blinka Keeper: size first, then defusedxml with no DTD at all, then depth.

A DTD is refused outright, so no entity is ever expanded (billion laughs) or fetched (XXE). An invoice never needs one.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from custodio.extraction.einvoice.errors import UnsafeXml
from custodio.extraction.errors import UnreadableDocument

MAX_XML_BYTES = 2 * 1024 * 1024  # a DIAN AttachedDocument with its signatures weighs tens of kilobytes
MAX_DEPTH = 40  # UBL nests about a dozen levels; far more is an attack on the parser, not an invoice


def parse(data: bytes) -> Element:
    if len(data) > MAX_XML_BYTES:
        raise UnsafeXml(f"El XML pesa {len(data):,} bytes; Blinka Keeper lee hasta {MAX_XML_BYTES:,}.")
    try:
        root = fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException as error:
        raise UnsafeXml("El XML declara un DTD o entidades; una factura no los necesita y no se procesa.") from error
    except ParseError as error:
        raise UnreadableDocument(f"El archivo no es un XML bien formado ({error}).") from error
    _ensure_shallow(root)
    return root


def _ensure_shallow(root: Element) -> None:
    pending = [(root, 1)]
    while pending:
        element, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise UnsafeXml(f"El XML anida más de {MAX_DEPTH} niveles; no es una factura.")
        pending.extend((child, depth + 1) for child in element)
