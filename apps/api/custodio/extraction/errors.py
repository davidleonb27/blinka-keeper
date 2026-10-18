"""Typed failures of the reading pipeline. Callers escalate or answer "NO MEDIDO"; they never guess."""

from __future__ import annotations


class ExtractionError(RuntimeError):
    """A document could not be read well enough to produce an ExtractedInvoice."""


class UnsupportedDocument(ExtractionError):
    """The file type is not one Blinka Keeper reads (PDF, PNG, JPEG, WebP or plain text)."""


class UnreadableDocument(ExtractionError):
    """The file claims a supported type but its bytes cannot be parsed or rendered."""


class MalformedReading(ExtractionError):
    """The model returned an object that parses but breaks the reading contract."""


class AmountFormatError(ValueError):
    """Text that does not read as exactly one amount in a known format."""


class UnsupportedHiddenText(ExtractionError):
    """Hidden text was requested for a channel that has no way to hide it (plain text, email)."""
