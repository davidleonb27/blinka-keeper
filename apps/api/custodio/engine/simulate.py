"""What a policy change would do: the same cases decided under both policies, side by side."""

from __future__ import annotations

from collections.abc import Sequence

from custodio.contracts import (
    AgentVerdict,
    CompanyState,
    Decision,
    InvoiceCase,
    Policy,
    RuleOutcome,
    SimulatedChange,
    SimulationReport,
)
from custodio.engine.decide import decide_all

PAID_UNDER_NEW_POLICY = "Con la política nueva se paga sola: se cumplen las {count} reglas."


def simulate(cases: Sequence[InvoiceCase], state: CompanyState, before: Policy, after: Policy) -> SimulationReport:
    old, new = decide_all(cases, state, before), decide_all(cases, state, after)
    old_by_id = {decision.invoice_id: decision for decision in old.decisions}
    changed = [
        SimulatedChange(
            invoice_id=decision.invoice_id,
            supplier_name=decision.supplier_name,
            before=old_by_id[decision.invoice_id].status,
            after=decision.status,
            reason=_why(decision),
        )
        for decision in new.decisions
        if decision.status is not old_by_id[decision.invoice_id].status
    ]
    return SimulationReport(before=old.metrics, after=new.metrics, changed=changed)


def _why(decision: Decision) -> str:
    """The first rule that now holds it, else the first that now escalates it; or that it is paid alone."""
    if decision.agent_verdict is AgentVerdict.PAY:
        return PAID_UNDER_NEW_POLICY.format(count=len(decision.rules))
    for outcome in (RuleOutcome.HOLD, RuleOutcome.ESCALATE):
        reason = next((rule.reason for rule in decision.rules if rule.outcome is outcome), None)
        if reason is not None:
            return reason
    return decision.blocked_reason or decision.explanation
