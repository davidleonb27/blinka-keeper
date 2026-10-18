"""The signed receipt of one decision: what a third party checks without any access to Blinka Keeper.

Every leaf of the body is a string, an integer, a boolean or null (amounts and dates travel as their canonical text),
so the canonical JSON that is signed reads the same in Python, in a browser and in a shell script.
"""

from __future__ import annotations

from typing import Final, Literal

from pydantic import Field

from custodio.contracts import AgentVerdict, DecisionStatus, Model, RuleOutcome

RECEIPT_FORMAT: Final = "custodio-receipt/1"
ALGORITHM: Final = "Ed25519"

Verdict = Literal["pay", "hold", "escalate", "reject"]


class ReceiptInvoice(Model):
    id: str
    number: str | None
    received_at: str
    source: str
    document_id: str | None
    document_sha256: str | None  # the bytes Blinka Keeper read; null when the invoice arrived as an intent with no file


class ReadField(Model):
    value: str | None
    verified: bool  # the quote exists in the document and supports the value, checked by code


class ReceiptRule(Model):
    rule_id: str
    outcome: RuleOutcome


class ReceiptPolicy(Model):
    version: int
    sha256: str | None  # canonical JSON of the policy in force when the decision was taken
    ledger_seq: int | None  # the policy_changed entry that put that version in force
    ledger_hash: str | None


class ReceiptDecision(Model):
    verdict: Verdict
    status: DecisionStatus
    agent_verdict: AgentVerdict
    approved_by: str | None


class ReceiptPayment(Model):
    """Only for a decision to pay: what the rail may send, to whom and where. The account travels as a fingerprint."""

    beneficiary_id: str | None
    beneficiary_name: str
    account_last4: str | None
    account_sha256: str | None
    amount: str
    currency: str | None
    amount_base: str
    base_currency: str
    rail: str | None
    external_id: str | None  # e.g. the Stripe transfer id, once the payment went out


class ReceiptLedger(Model):
    seq: int
    hash: str
    kind: str


class ReceiptBody(Model):
    format: Literal["custodio-receipt/1"] = RECEIPT_FORMAT
    key_id: str
    workspace_id: str
    issued_at: str  # when the decision entered the ledger, so the same decision always gives the same receipt
    invoice: ReceiptInvoice
    reading: dict[str, ReadField]
    rules: list[ReceiptRule]
    policy: ReceiptPolicy
    decision: ReceiptDecision
    payment: ReceiptPayment | None
    ledger: ReceiptLedger


class DecisionReceipt(Model):
    """`signature` signs the canonical body; `digests_signature` signs one SHA-256 per field of the body, which is how
    a verifier names the field that was altered instead of only saying that something was."""

    format: Literal["custodio-receipt/1"] = RECEIPT_FORMAT
    algorithm: Literal["Ed25519"] = ALGORITHM
    key_id: str
    body: ReceiptBody
    signature: str  # standard base64
    field_digests: dict[str, str]  # "payment.amount" → sha256 of that value's canonical JSON
    digests_signature: str


class ReceiptKey(Model):
    """The public half, served at /api/v1/.well-known/custodio-receipt-key."""

    format: Literal["custodio-receipt/1"] = RECEIPT_FORMAT
    algorithm: Literal["Ed25519"] = ALGORITHM
    key_id: str
    public_key: str  # the raw 32 bytes, standard base64
    public_key_pem: str  # SubjectPublicKeyInfo, for openssl


class ReceiptCheck(Model):
    valid: bool
    message: str  # Spanish, for the person who pasted the receipt
    key_id: str | None = None
    invoice_id: str | None = None
    verdict: Verdict | None = None
    altered_fields: list[str] = Field(default_factory=list)  # paths, e.g. "payment.amount"
    altered_labels: list[str] = Field(default_factory=list)  # the same, as a person reads them: «monto»
