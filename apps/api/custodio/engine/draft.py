"""A decision in the making, shared by decide (which builds it) and explain (which puts it into words)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from custodio.contracts import AgentVerdict, Approval, Beneficiary, DecisionStatus
from custodio.engine.facts import InvoiceFacts
from custodio.engine.rules import RuleCheck


@dataclass(frozen=True)
class Draft:
    facts: InvoiceFacts
    beneficiary: Beneficiary | None
    checks: tuple[RuleCheck, ...]
    verdict: AgentVerdict
    status: DecisionStatus
    balance_before: Decimal
    balance_after: Decimal
    spent_after: Decimal  # the agent's own spending in the invoice's month, after this decision
    approval: Approval | None = None
    blocked_reason: str | None = None
