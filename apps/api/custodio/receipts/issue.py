"""What a receipt says about one decision, built only from what was decided and recorded. Pure."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from custodio.contracts import Beneficiary, Decision, DecisionStatus, InvoiceCase, LedgerEntry
from custodio.engine.ledger import canonical_json
from custodio.receipts.models import (
    ReadField,
    ReceiptBody,
    ReceiptDecision,
    ReceiptInvoice,
    ReceiptLedger,
    ReceiptPayment,
    ReceiptPolicy,
    ReceiptRule,
    Verdict,
)

READ_FIELDS = (
    "supplier_name",
    "supplier_tax_id",
    "invoice_number",
    "issue_date",
    "due_date",
    "amount",
    "currency",
    "bank_name",
    "account_number",
)
VERDICTS: dict[DecisionStatus, Verdict] = {
    DecisionStatus.PAID_AUTO: "pay",
    DecisionStatus.PAID_HUMAN: "pay",
    DecisionStatus.HOLD: "hold",
    DecisionStatus.PENDING_APPROVAL: "escalate",
    DecisionStatus.REJECTED: "reject",
}
LAST_DIGITS = 4


@dataclass(frozen=True)
class DecisionFacts:
    workspace_id: str
    decision: Decision
    invoice: InvoiceCase
    document_sha256: str | None
    policy: ReceiptPolicy
    entry: LedgerEntry  # the decision (or approval) entry of this invoice in the ledger
    beneficiary: Beneficiary | None  # the registered one, never the invoice's bank details
    base_currency: str


def build_body(facts: DecisionFacts, key_id: str) -> ReceiptBody:
    decision = facts.decision
    extraction = facts.invoice.extraction
    verdict = VERDICTS[decision.status]
    return ReceiptBody(
        key_id=key_id,
        workspace_id=facts.workspace_id,
        issued_at=_moment(facts.entry.at),
        invoice=ReceiptInvoice(
            id=facts.invoice.id,
            number=extraction.invoice_number.value,
            received_at=_moment(facts.invoice.received_at),
            source=extraction.source.value,
            document_id=extraction.document_id or None,
            document_sha256=facts.document_sha256,
        ),
        reading={
            name: ReadField(value=getattr(extraction, name).value, verified=getattr(extraction, name).verified)
            for name in READ_FIELDS
        },
        rules=[ReceiptRule(rule_id=rule.rule_id, outcome=rule.outcome) for rule in decision.rules],
        policy=facts.policy,
        decision=ReceiptDecision(
            verdict=verdict,
            status=decision.status,
            agent_verdict=decision.agent_verdict,
            approved_by=decision.approval.approver if decision.approval else None,
        ),
        payment=_payment(facts) if verdict == "pay" else None,
        ledger=ReceiptLedger(seq=facts.entry.seq, hash=facts.entry.hash, kind=facts.entry.kind.value),
    )


def amount_text(value: Decimal) -> str:
    """The canonical spelling of an amount: the same one the ledger hashes."""
    text: str = json.loads(canonical_json(value))
    return text


def account_fingerprint(account_number: str) -> str:
    return hashlib.sha256(_compact(account_number).encode()).hexdigest()


def policy_digest(document: object) -> str:
    return hashlib.sha256(canonical_json(document).encode()).hexdigest()


def _payment(facts: DecisionFacts) -> ReceiptPayment:
    decision = facts.decision
    registered = facts.beneficiary
    amount_base = decision.amount_base or Decimal(0)
    account = registered.account_number if registered else None
    execution = decision.execution
    return ReceiptPayment(
        beneficiary_id=decision.beneficiary_id,
        beneficiary_name=registered.name if registered else decision.supplier_name or "",
        account_last4=_compact(account)[-LAST_DIGITS:] if account else None,
        account_sha256=account_fingerprint(account) if account else None,
        amount=amount_text(decision.amount if decision.amount is not None else amount_base),
        currency=decision.currency,
        amount_base=amount_text(amount_base),
        base_currency=facts.base_currency,
        rail=execution.rail if execution else None,
        external_id=execution.external_id if execution else None,
    )


def _compact(account_number: str) -> str:
    return "".join(account_number.split())


def _moment(value: datetime) -> str:
    text: str = json.loads(canonical_json(value))
    return text
