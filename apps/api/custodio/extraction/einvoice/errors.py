"""Why an XML is refused: it is unsafe to parse, or it is not an electronic invoice Blinka Keeper reads."""

from __future__ import annotations

from custodio.extraction.errors import UnreadableDocument, UnsupportedDocument


class UnsafeXml(UnreadableDocument):
    """Refused before or while parsing: a DTD or entities (billion laughs, XXE), too many bytes or too deep."""


class NotAnEInvoice(UnsupportedDocument):
    """Well-formed XML that is neither a DIAN UBL 2.1 invoice nor a CFDI 4.0."""
