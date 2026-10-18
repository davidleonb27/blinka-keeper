"""A receipt body with every section filled, and a key that is the same on every run."""

from __future__ import annotations

from custodio.contracts import AgentVerdict, DecisionStatus, RuleOutcome
from custodio.receipts import (
    ReadField,
    ReceiptBody,
    ReceiptDecision,
    ReceiptInvoice,
    ReceiptLedger,
    ReceiptPayment,
    ReceiptPolicy,
    ReceiptRule,
    ReceiptSigner,
)

FIXED_SEED = bytes(range(32))
OTHER_SEED = bytes(range(1, 33))


def fixed_signer() -> ReceiptSigner:
    return ReceiptSigner.from_seed(FIXED_SEED)


def other_signer() -> ReceiptSigner:
    return ReceiptSigner.from_seed(OTHER_SEED)


def sample_body(key_id: str, *, verdict: str = "pay") -> ReceiptBody:
    paid = verdict == "pay"
    return ReceiptBody(
        key_id=key_id,
        workspace_id="ws-ejemplo",
        issued_at="2026-10-17T15:00:00Z",
        invoice=ReceiptInvoice(
            id="INV-0001",
            number="FE-2291",
            received_at="2026-10-17T14:58:12.5Z",
            source="pdf",
            document_id="doc-1",
            document_sha256="ab" * 32,
        ),
        reading={
            "supplier_name": ReadField(value="Andes Código S.A.S.", verified=True),
            "amount": ReadField(value="4200.00", verified=True),
            "currency": ReadField(value="USD", verified=True),
            "account_number": ReadField(value="000123456789", verified=True),
        },
        rules=[
            ReceiptRule(rule_id="R1", outcome=RuleOutcome.PASS),
            ReceiptRule(rule_id="R4", outcome=RuleOutcome.PASS if paid else RuleOutcome.HOLD),
        ],
        policy=ReceiptPolicy(version=3, sha256="cd" * 32, ledger_seq=2, ledger_hash="ef" * 32),
        decision=ReceiptDecision(
            verdict="pay" if paid else "hold",
            status=DecisionStatus.PAID_AUTO if paid else DecisionStatus.HOLD,
            agent_verdict=AgentVerdict.PAY if paid else AgentVerdict.HOLD,
            approved_by=None,
        ),
        payment=ReceiptPayment(
            beneficiary_id="b-andes",
            beneficiary_name="Andes Código S.A.S.",
            account_last4="6789",
            account_sha256="12" * 32,
            amount="4200",
            currency="USD",
            amount_base="4200",
            base_currency="USD",
            rail=None,
            external_id=None,
        )
        if paid
        else None,
        ledger=ReceiptLedger(seq=7, hash="9a" * 32, kind="decision"),
    )
