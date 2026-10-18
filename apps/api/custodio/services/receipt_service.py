"""Issuing and checking signed receipts. What a receipt says comes from the stored decision and the ledger only."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import select

from custodio.contracts import Decision, LedgerEntry, LedgerKind, Policy
from custodio.db.models import DocumentRow, PolicyRow
from custodio.receipts import (
    DecisionFacts,
    DecisionReceipt,
    ReceiptCheck,
    ReceiptKey,
    ReceiptPolicy,
    build_body,
    example_body,
    policy_digest,
    sign_receipt,
    verify_receipt,
)
from custodio.services import ledger_service, policy_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import ReceiptUnavailable

DECIDING_KINDS = (LedgerKind.DECISION, LedgerKind.APPROVAL)


def key(ctx: ServiceContext) -> ReceiptKey:
    return ctx.receipt_signer.public_key.view()


def check(ctx: ServiceContext, raw: object) -> ReceiptCheck:
    return verify_receipt(raw, ctx.receipt_signer.public_key)


def for_invoice(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> DecisionReceipt:
    """The receipt of the decision as stored, with the payment's external id once it went out."""
    decision = records.decision(ctx, workspace_id, invoice_id)
    return issue(ctx, workspace_id, decision, policy_service.current(ctx, workspace_id))


def issue(ctx: ServiceContext, workspace_id: str, decision: Decision, policy: Policy) -> DecisionReceipt:
    """Signs `decision` as given: the payment service passes the amount the rail will send (less any discount)."""
    entries = ledger_service.entries(ctx, workspace_id, subject_id=decision.invoice_id, kinds=DECIDING_KINDS)
    if not entries:
        raise ReceiptUnavailable()
    entry = entries[-1]
    if entry.payload.get("status") != decision.status.value:
        raise ReceiptUnavailable()  # the ledger recorded another outcome: nothing is signed that it does not show
    invoice = records.invoice(ctx, workspace_id, decision.invoice_id)
    facts = DecisionFacts(
        workspace_id=workspace_id,
        decision=decision,
        invoice=records.as_case(invoice),
        document_id=invoice.document_id,
        document_sha256=_document_digest(ctx, workspace_id, invoice.document_id),
        policy=_policy_in_force(ctx, workspace_id, entry, policy),
        entry=entry,
        beneficiary=next((b for b in policy.beneficiaries if b.id == decision.beneficiary_id), None),
        base_currency=policy.base_currency,
    )
    signer = ctx.receipt_signer
    return sign_receipt(build_body(facts, signer.key_id), signer)


def _document_digest(ctx: ServiceContext, workspace_id: str, document_id: str | None) -> str | None:
    if document_id is None:
        return None
    data = ctx.session.scalar(
        select(DocumentRow.data).where(DocumentRow.workspace_id == workspace_id, DocumentRow.id == document_id)
    )
    return hashlib.sha256(data).hexdigest() if data is not None else None


def _policy_in_force(ctx: ServiceContext, workspace_id: str, decided: LedgerEntry, current: Policy) -> ReceiptPolicy:
    """The last policy change written before the decision; the current version if the ledger has none."""
    changes = ledger_service.entries(ctx, workspace_id, kinds=(LedgerKind.POLICY_CHANGED,))
    change = next((entry for entry in reversed(changes) if entry.seq < decided.seq), None)
    version = _version(change.payload, current.version) if change else current.version
    document = ctx.session.scalar(
        select(PolicyRow.document).where(PolicyRow.workspace_id == workspace_id, PolicyRow.version == version)
    )
    return ReceiptPolicy(
        version=version,
        sha256=policy_digest(document) if document is not None else None,
        ledger_seq=change.seq if change else None,
        ledger_hash=change.hash if change else None,
    )


def _version(payload: dict[str, Any], fallback: int) -> int:
    version = payload.get("version")
    return version if isinstance(version, int) else fallback


def example(ctx: ServiceContext) -> DecisionReceipt:
    signer = ctx.receipt_signer
    return sign_receipt(example_body(signer.key_id), signer)
