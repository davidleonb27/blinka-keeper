"""A receipt of a made-up decision, for the public check page's «try an altered receipt» button.

It is signed with the deployment's real key, so it verifies like any other, and says plainly that it is an example:
its workspace is «ejemplo» and nothing in it points to a real invoice or ledger.
"""

from __future__ import annotations

from custodio.contracts import RULES, AgentVerdict, DecisionStatus, RuleOutcome
from custodio.receipts.models import (
    ReadField,
    ReceiptBody,
    ReceiptDecision,
    ReceiptInvoice,
    ReceiptLedger,
    ReceiptPayment,
    ReceiptPolicy,
    ReceiptRule,
)

EXAMPLE_WORKSPACE = "ejemplo"
_NO_HASH = "0" * 64


def example_body(key_id: str) -> ReceiptBody:
    return ReceiptBody(
        key_id=key_id,
        workspace_id=EXAMPLE_WORKSPACE,
        issued_at="2026-10-17T15:00:00Z",
        invoice=ReceiptInvoice(
            id="EJEMPLO-0001",
            number="FE-0001",
            received_at="2026-10-17T14:58:00Z",
            source="pdf",
            document_id=None,
            document_sha256=None,
        ),
        reading={
            "supplier_name": ReadField(value="Proveedor de Ejemplo S.A.S.", verified=True),
            "amount": ReadField(value="4200.00", verified=True),
            "currency": ReadField(value="USD", verified=True),
            "account_number": ReadField(value="000123456789", verified=True),
        },
        rules=[ReceiptRule(rule_id=rule.id, outcome=RuleOutcome.PASS) for rule in RULES],
        policy=ReceiptPolicy(version=1, sha256=None, ledger_seq=None, ledger_hash=None),
        decision=ReceiptDecision(
            verdict="pay", status=DecisionStatus.PAID_AUTO, agent_verdict=AgentVerdict.PAY, approved_by=None
        ),
        payment=ReceiptPayment(
            beneficiary_id="ejemplo",
            beneficiary_name="Proveedor de Ejemplo S.A.S.",
            account_last4="6789",
            account_sha256=None,
            amount="4200",
            currency="USD",
            amount_base="4200",
            base_currency="USD",
            rail="simulated",
            external_id=None,
        ),
        ledger=ReceiptLedger(seq=1, hash=_NO_HASH, kind="decision"),
    )
