"""What a stopped invoice needs from its supplier: the causes they can fix and the ones never negotiated with them."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class IssueKind(StrEnum):
    AMOUNT_MISMATCH = "amount_mismatch"  # R6: off the fixed agreement
    CURRENCY_MISMATCH = "currency_mismatch"  # R6: not the agreed currency
    CURRENCY_NOT_ALLOWED = "currency_not_allowed"  # R8, when the agreed currency is allowed
    AMOUNT_UNREADABLE = "amount_unreadable"  # R1
    CURRENCY_UNCLEAR = "currency_unclear"  # R1, e.g. a bare "$"
    FIELD_UNREADABLE = "field_unreadable"  # R1 on a field the supplier can only fix with a legible document
    MISSING_INVOICE_NUMBER = "missing_invoice_number"
    INVALID_DATE = "invalid_date"
    TOTAL_MISMATCH = "total_mismatch"  # subtotal and taxes do not add up to the total


class BlockerKind(StrEnum):
    ACCOUNT_CHANGED = "account_changed"  # R4, or R15 on an account change
    BANK_DETAILS = "bank_details"  # R13
    DUPLICATE = "duplicate"  # R5
    HIDDEN_INSTRUCTION = "hidden_instruction"  # R2
    UNREGISTERED_SUPPLIER = "unregistered_supplier"  # R3
    SANCTIONS = "sanctions"  # R14
    SENDER_DOMAIN = "sender_domain"  # R15 on a look-alike sender domain
    SPLIT = "split"  # R7
    RESERVE = "reserve"  # R12
    POLICY_CURRENCY = "policy_currency"  # R8 when the agreed currency itself is not allowed


class CorrectableField(StrEnum):
    """What a supplier may type instead of sending a new document. Never an account or a supplier identity."""

    AMOUNT = "amount"
    CURRENCY = "currency"
    INVOICE_NUMBER = "invoice_number"
    ISSUE_DATE = "issue_date"


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: IssueKind
    rule_id: str | None  # None for the form checks the fifteen rules do not cover
    fields: list[CorrectableField]  # empty: only a corrected document fixes it
    problem: str  # Spanish, built from the rule's numbers and the registered data, never from the document's words
    expected: str  # Spanish: what the agreement or the policy expects


class Blocker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: BlockerKind
    rule_id: str
    reason: str  # Spanish: why this is not negotiated with the supplier


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[Issue]
    blockers: list[Blocker]
    still_for_a_person: list[str]  # rules a person still decides after a correction (e.g. R9), as their labels

    @property
    def correctable(self) -> bool:
        return bool(self.issues) and not self.blockers

    @property
    def fields(self) -> list[CorrectableField]:
        """Every field the supplier may confirm by typing it, once, in the order the issues ask for them."""
        return list(dict.fromkeys(name for issue in self.issues for name in issue.fields))

    @property
    def confirmable(self) -> bool:
        """True when typing the fields fixes every issue; otherwise only a corrected document does."""
        return self.correctable and all(issue.fields for issue in self.issues)
