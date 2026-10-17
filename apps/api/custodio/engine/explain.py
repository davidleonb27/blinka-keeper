"""Deterministic Spanish text for a decision: what happened and what would have made it payable alone."""

from __future__ import annotations

from collections.abc import Sequence

from custodio.contracts import AgentVerdict, DecisionStatus, RuleOutcome, RuleResult
from custodio.engine.draft import Draft
from custodio.engine.formatting import day_month, join_es
from custodio.engine.units import as_utc

COUNTERFACTUAL = "Se habría pagado sola si {conditions}."
PAID_HIGHLIGHTS = ("R3", "R4", "R9", "R12", "R11")
UNEXPLAINED_CONDITION = "todas las reglas se pudieran comprobar y el auditor independiente estuviera de acuerdo"


def rules_met(results: Sequence[RuleResult]) -> str:
    """`se cumplen las 15 reglas`, or how many applied when a payment control had nothing to check."""
    skipped = [result.rule_id for result in results if result.outcome is RuleOutcome.SKIPPED]
    if not skipped:
        return f"se cumplen las {len(results)} reglas"
    verb = "tenía" if len(skipped) == 1 else "tenían"
    applied = len(results) - len(skipped)
    return f"se cumplen las {applied} reglas que aplican ({join_es(skipped)} no {verb} nada que comprobar)"


def explanation(draft: Draft) -> str:
    parts = (_what_the_agent_did(draft), _what_the_person_did(draft))
    return " ".join(part for part in parts if part)


def counterfactual(draft: Draft) -> str | None:
    """None when the agent paid; otherwise the minimum change, one condition per failed rule."""
    if draft.verdict is AgentVerdict.PAY:
        return None
    conditions = list(dict.fromkeys(check.fix for check in draft.checks if check.fix))
    return COUNTERFACTUAL.format(conditions=join_es(conditions or [UNEXPLAINED_CONDITION]))


def _what_the_agent_did(draft: Draft) -> str:
    if draft.verdict is AgentVerdict.PAY:
        return _paid_alone(draft)
    holds = _reasons(draft, RuleOutcome.HOLD)
    escalations = _reasons(draft, RuleOutcome.ESCALATE) or _reasons(draft, RuleOutcome.SKIPPED)
    if draft.verdict is AgentVerdict.HOLD:
        also = f" Además: {' '.join(escalations)}" if escalations else ""
        return f"Se retiene: no se paga. {' '.join(holds)}".rstrip() + also
    return f"Se pide aprobación a una persona. {' '.join(escalations)} El agente no paga esto sin aprobación."


def _paid_alone(draft: Draft) -> str:
    """Every rule passed; the reasons that matter most to a reader already carry the numbers."""
    reasons = {check.result.rule_id: check.result.reason for check in draft.checks}
    highlights = " ".join(reasons[rule_id] for rule_id in PAID_HIGHLIGHTS)
    return f"Se paga sola: {rules_met([check.result for check in draft.checks])}. {highlights}"


def _what_the_person_did(draft: Draft) -> str | None:
    given = draft.approval
    if given is None:
        return draft.blocked_reason
    when = day_month(as_utc(given.at).date())
    if draft.status is DecisionStatus.PAID_HUMAN:
        return f"{given.approver} lo aprobó el {when} y se pagó con su autorización."
    if given.decision == "rejected":
        return f"{given.approver} lo rechazó el {when}."
    return f"{given.approver} lo aprobó, pero no se paga: {draft.blocked_reason}"


def _reasons(draft: Draft, outcome: RuleOutcome) -> list[str]:
    return [check.result.reason for check in draft.checks if check.result.outcome is outcome]
