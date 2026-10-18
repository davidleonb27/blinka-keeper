"""Supplier corrections (L23): what a stopped invoice needs from its supplier, said and taken back safely.

Pure functions only. The service (`custodio.services.correction_service`) stores the requests, issues the links and
sends the corrected invoice down the same path as any other: reading, the fifteen rules, the auditor and the ledger.
"""

from custodio.corrections.causes import assess
from custodio.corrections.confirmation import MAX_CONFIRMED_LENGTH, ConfirmationInvalid, corrected_text
from custodio.corrections.message import compose_message, safe_reference
from custodio.corrections.models import Assessment, Blocker, BlockerKind, CorrectableField, Issue, IssueKind

__all__ = [
    "MAX_CONFIRMED_LENGTH",
    "Assessment",
    "Blocker",
    "BlockerKind",
    "ConfirmationInvalid",
    "CorrectableField",
    "Issue",
    "IssueKind",
    "assess",
    "compose_message",
    "corrected_text",
    "safe_reference",
]
