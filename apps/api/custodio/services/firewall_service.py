"""Payment firewall for other agents (HTTP and MCP).

A payment intent is written out as the document it claims to be and goes through the very same path as an invoice
uploaded in the panel: read it, decide it with the workspace's rules and history, audit it, record it.
"""

from __future__ import annotations

from custodio.contracts import Decision, IntentVerdict, InvoiceSource, LedgerKind, PaymentIntent
from custodio.db.models import WorkspaceRow
from custodio.services import invoice_service, ledger_service, records
from custodio.services.context import ServiceContext


def submit(ctx: ServiceContext, workspace: WorkspaceRow, intent: PaymentIntent) -> IntentVerdict:
    received = invoice_service.receive_text(ctx, workspace, intent_document(intent), source=InvoiceSource.INTENT)
    ledger_service.append(ctx, workspace.id, LedgerKind.INTENT, received.id, _intent_payload(intent))
    outcome = invoice_service.decide(ctx, workspace, [records.invoice(ctx, workspace.id, received.id)])
    decision = outcome.batch.decisions[0]
    return IntentVerdict(
        decision=decision,
        ledger_hash=_decision_hash(ctx, workspace.id, decision),
        acta_url=acta_url(ctx.runtime.public_base_url, decision.invoice_id),
    )


def intent_document(intent: PaymentIntent) -> str:
    """The intent as a plain-text invoice. The attached document text goes along so hidden instructions are seen."""
    lines = [
        f"Solicitud de pago enviada por el agente: {intent.agent}",
        f"Proveedor: {intent.beneficiary_name}",
        f"Identificación tributaria: {intent.beneficiary_tax_id or ''}",
        f"Número de factura: {intent.invoice_number}",
        f"Fecha de emisión: {intent.issue_date.isoformat() if intent.issue_date else ''}",
        f"Monto: {intent.amount}",
        f"Moneda: {intent.currency}",
        f"Banco: {intent.bank_name or ''}",
        f"Cuenta: {intent.account_number}",
        f"Concepto: {intent.description}",
    ]
    if intent.document_text:
        lines += ["", "Documento adjunto:", intent.document_text]
    return "\n".join(lines)


def acta_url(public_base_url: str, invoice_id: str) -> str:
    return f"{public_base_url.rstrip('/')}/acta/{invoice_id}"


def _intent_payload(intent: PaymentIntent) -> dict[str, str | None]:
    return {
        "agent": intent.agent,
        "beneficiary_name": intent.beneficiary_name,
        "invoice_number": intent.invoice_number,
        "amount": str(intent.amount),
        "currency": intent.currency,
    }


def _decision_hash(ctx: ServiceContext, workspace_id: str, decision: Decision) -> str:
    recorded = ledger_service.entries(ctx, workspace_id, subject_id=decision.invoice_id)
    return next(entry.hash for entry in reversed(recorded) if entry.kind is LedgerKind.DECISION)
