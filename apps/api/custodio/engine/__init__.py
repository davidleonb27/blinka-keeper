"""Deterministic decision engine. Owned by lane L1.

Pure functions only: same inputs, same outputs. No I/O, no clock, no randomness, no model calls. The engine
never reads `InvoiceCase.expected` or `InvoiceCase.trap`. Semantics are ported from prototype/engine.js
(`decideAll`, `audit`, `counterfactual`, `explain`) and specified in docs/DESIGN.md §5.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from custodio.contracts import (
    Approval,
    AuditReport,
    BatchResult,
    CompanyState,
    InvoiceCase,
    Policy,
    SimulationReport,
)


def decide_all(
    cases: Sequence[InvoiceCase],
    state: CompanyState,
    policy: Policy,
    approvals: Mapping[str, Approval] | None = None,
) -> BatchResult:
    """Decide every case in arrival order, then apply approvals at approval time (never breaching the reserve)."""
    raise NotImplementedError("lane L1")


def audit(batch: BatchResult, cases: Sequence[InvoiceCase], state: CompanyState, policy: Policy) -> AuditReport:
    """Independently re-check every payment in `batch` without reusing decide_all's code paths."""
    raise NotImplementedError("lane L1")


def simulate(cases: Sequence[InvoiceCase], state: CompanyState, before: Policy, after: Policy) -> SimulationReport:
    """Decide the same cases under two policies and report what would change."""
    raise NotImplementedError("lane L1")
