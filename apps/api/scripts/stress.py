"""Stress run: many random companies, each with a random batch and random approvals, re-checked by the auditor.

Usage: uv run python scripts/stress.py --companies 1000 --seed 7

Prints one JSON report. The run fails (exit code 1) if the auditor finds any improper payment, if the engine ever
needed an auditor veto, if a balance ends under its reserve, or if the agent paid a trap on its own.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# `uv run python scripts/stress.py` puts scripts/ on sys.path, not the project root where `custodio` lives.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custodio.contracts import Decision, DecisionStatus
from custodio.dataset.synthetic import random_approvals, random_batch, random_company
from custodio.engine import audit, decide_all

MIN_BATCH, MAX_BATCH = 10, 40
VETO_PREFIX = "El auditor independiente"
PAID = (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN)


def run(*, companies: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)  # noqa: S311 - a seeded simulation must replay, not resist prediction
    statuses: Counter[str] = Counter()
    traps: Counter[str] = Counter()
    traps_paid: Counter[str] = Counter()
    checked = improper = vetoes = reserve_breaches = approvals_given = 0
    started = time.perf_counter()
    for index in range(companies):
        state, policy = random_company(rng, workspace_id=f"stress-{index}")
        cases = random_batch(rng, state, policy, size=rng.randint(MIN_BATCH, MAX_BATCH))
        approvals = random_approvals(rng, decide_all(cases, state, policy).decisions)
        batch = decide_all(cases, state, policy, approvals)
        report = audit(batch, cases, state, policy)
        trap_of = {case.id: case.trap or "normal" for case in cases}
        statuses.update(decision.status.value for decision in batch.decisions)
        traps.update(trap_of.values())
        traps_paid.update(
            trap_of[d.invoice_id]
            for d in batch.decisions
            if d.status is DecisionStatus.PAID_AUTO and trap_of[d.invoice_id] != "normal"
        )
        checked += report.checked
        improper += report.improper_payments
        vetoes += sum(1 for d in batch.decisions if _vetoed(d))
        reserve_breaches += int(any(d.status in PAID for d in batch.decisions) and batch.balance_end < policy.reserve)
        approvals_given += len(approvals)
    seconds = time.perf_counter() - started
    invoices = sum(statuses.values())
    return {
        "companies": companies,
        "seed": seed,
        "invoices": invoices,
        "approvals_given": approvals_given,
        "statuses": dict(sorted(statuses.items())),
        "traps": dict(sorted(traps.items())),
        "payments_checked_by_auditor": checked,
        "improper_payments": improper,
        "auditor_vetoes": vetoes,
        "reserve_breaches": reserve_breaches,
        "traps_paid_by_agent": dict(sorted(traps_paid.items())),
        "seconds": round(seconds, 2),
        "invoices_per_second": round(invoices / seconds, 1) if seconds else None,
    }


def _vetoed(decision: Decision) -> bool:
    return bool(decision.blocked_reason and decision.blocked_reason.startswith(VETO_PREFIX))


def _healthy(report: dict[str, Any]) -> bool:
    return (
        report["improper_payments"] == 0
        and report["auditor_vetoes"] == 0
        and report["reserve_breaches"] == 0
        and not report["traps_paid_by_agent"]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--companies", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    report = run(companies=args.companies, seed=args.seed)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if _healthy(report) else 1


if __name__ == "__main__":
    sys.exit(main())
