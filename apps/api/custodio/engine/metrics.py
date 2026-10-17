"""Batch metrics. This is the only module that reads `InvoiceCase.expected`, and only to score the batch."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from custodio.contracts import AgentVerdict, Decision, DecisionStatus, InvoiceCase, Metrics


def compute_metrics(decisions: Sequence[Decision], cases: Sequence[InvoiceCase], *, improper_payments: int) -> Metrics:
    counts = Counter(decision.status for decision in decisions)
    total = len(decisions)
    # By the agent's own verdict: an approval the reserve then blocks also ends in `hold`, but a person decided it.
    decided_alone = sum(1 for d in decisions if d.agent_verdict in (AgentVerdict.PAY, AgentVerdict.HOLD))
    return Metrics(
        total=total,
        paid_auto=counts[DecisionStatus.PAID_AUTO],
        paid_human=counts[DecisionStatus.PAID_HUMAN],
        hold=counts[DecisionStatus.HOLD],
        pending=counts[DecisionStatus.PENDING_APPROVAL],
        rejected=counts[DecisionStatus.REJECTED],
        autonomy_rate=decided_alone / total if total else 0.0,
        accuracy=_accuracy(decisions, cases),
        improper_payments=improper_payments,
    )


def _accuracy(decisions: Sequence[Decision], cases: Sequence[InvoiceCase]) -> float | None:
    """Share of labelled cases whose agent verdict matches the label; None when nothing is labelled."""
    labels = {case.id: case.expected for case in cases if case.expected is not None}
    if not labels:
        return None
    right = sum(1 for d in decisions if d.invoice_id in labels and d.agent_verdict.value == labels[d.invoice_id])
    return right / len(labels)
