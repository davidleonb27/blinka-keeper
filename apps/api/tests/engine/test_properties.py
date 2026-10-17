"""Hypothesis properties: every invariant of docs/DESIGN.md §3 that the engine owns, on random companies and batches.

The random companies and batches come from custodio.dataset.synthetic, driven by a Hypothesis-controlled Random so
failures shrink and replay.
"""

import ast
import random
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from custodio.dataset.synthetic import random_approvals, random_batch, random_company
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from custodio.contracts import (
    AgentVerdict,
    Approval,
    BatchResult,
    CompanyState,
    DecisionStatus,
    InvoiceCase,
    Policy,
    RuleOutcome,
)
from custodio.engine import audit, decide_all

ENGINE = Path(__file__).parents[2] / "custodio" / "engine"
PAID = (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN)
VETO_PREFIX = "El auditor independiente"
PROPERTY = settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def scenario(rng: random.Random) -> tuple[list[InvoiceCase], CompanyState, Policy, dict[str, Approval]]:
    state, policy = random_company(rng, workspace_id="w-property")
    cases = random_batch(rng, state, policy, size=rng.randint(1, 30))
    approvals = random_approvals(rng, decide_all(cases, state, policy).decisions)
    return cases, state, policy, approvals


def paid_total(batch: BatchResult) -> Decimal:
    return sum((d.amount_base for d in batch.decisions if d.status in PAID and d.amount_base is not None), Decimal(0))


@PROPERTY
@given(rng=st.randoms(use_true_random=False))
def test_the_engine_is_deterministic(rng: random.Random) -> None:
    cases, state, policy, approvals = scenario(rng)
    assert decide_all(cases, state, policy, approvals) == decide_all(cases, state, policy, approvals)


@PROPERTY
@given(rng=st.randoms(use_true_random=False))
def test_nothing_is_paid_while_a_hold_rule_fails_not_even_with_approval(rng: random.Random) -> None:
    cases, state, policy, approvals = scenario(rng)
    for decision in decide_all(cases, state, policy, approvals).decisions:
        if decision.status in PAID:
            assert all(rule.outcome is not RuleOutcome.HOLD for rule in decision.rules)
        if decision.status is DecisionStatus.PAID_AUTO:
            assert all(rule.outcome is RuleOutcome.PASS for rule in decision.rules)


@PROPERTY
@given(rng=st.randoms(use_true_random=False))
def test_the_balance_never_ends_under_the_reserve_not_even_with_approvals(rng: random.Random) -> None:
    cases, state, policy, approvals = scenario(rng)
    batch = decide_all(cases, state, policy, approvals)
    payments = [d for d in batch.decisions if d.status in PAID]
    for decision in payments:
        assert decision.balance_after is not None and decision.balance_after >= policy.reserve
    assert batch.balance_end == state.opening_balance - paid_total(batch)
    if payments:
        assert batch.balance_end >= policy.reserve


@PROPERTY
@given(rng=st.randoms(use_true_random=False), data=st.data())
def test_approving_one_invoice_does_not_change_any_other(rng: random.Random, data: st.DataObject) -> None:
    cases, state, policy, approvals = scenario(rng)
    before = decide_all(cases, state, policy, approvals)
    open_ids = [d.invoice_id for d in before.decisions if d.status is DecisionStatus.PENDING_APPROVAL]
    if not open_ids:
        return
    chosen = data.draw(st.sampled_from(open_ids))
    late = datetime(2026, 12, 31, tzinfo=UTC)
    extra = Approval(invoice_id=chosen, decision="approved", approver="Ana Gómez", channel="web", at=late)
    after = decide_all(cases, state, policy, {**approvals, chosen: extra})
    for old, new in zip(before.decisions, after.decisions, strict=True):
        assert old.agent_verdict is new.agent_verdict
        if old.invoice_id != chosen:
            assert old == new


@PROPERTY
@given(rng=st.randoms(use_true_random=False))
def test_removing_expected_and_trap_changes_no_decision(rng: random.Random) -> None:
    cases, state, policy, approvals = scenario(rng)
    labelled = [case.model_copy(update={"expected": "pay", "trap": "etiqueta"}) for case in cases]
    blank = [case.model_copy(update={"expected": None, "trap": None}) for case in cases]
    with_labels = decide_all(labelled, state, policy, approvals)
    without = decide_all(blank, state, policy, approvals)
    assert with_labels.decisions == without.decisions
    assert (with_labels.balance_end, with_labels.spent_auto_base) == (without.balance_end, without.spent_auto_base)


@PROPERTY
@given(rng=st.randoms(use_true_random=False))
def test_the_auditor_agrees_with_the_engine_without_ever_needing_a_veto(rng: random.Random) -> None:
    cases, state, policy, approvals = scenario(rng)
    batch = decide_all(cases, state, policy, approvals)
    report = audit(batch, cases, state, policy)
    assert report.agrees and report.improper_payments == 0 == batch.metrics.improper_payments
    assert report.checked == sum(1 for d in batch.decisions if d.status in PAID)
    assert not any(d.blocked_reason and d.blocked_reason.startswith(VETO_PREFIX) for d in batch.decisions)


@PROPERTY
@given(rng=st.randoms(use_true_random=False))
def test_no_trap_is_ever_paid_by_the_agent_alone(rng: random.Random) -> None:
    cases, state, policy, _ = scenario(rng)
    traps = {case.id: case.trap for case in cases}
    paid_traps = [
        (d.invoice_id, traps[d.invoice_id])
        for d in decide_all(cases, state, policy).decisions
        if d.status is DecisionStatus.PAID_AUTO and traps[d.invoice_id] != "normal"
    ]
    assert paid_traps == []


@PROPERTY
@given(rng=st.randoms(use_true_random=False), text=st.text(min_size=1, max_size=200))
def test_document_text_never_makes_a_decision_more_permissive(rng: random.Random, text: str) -> None:
    cases, state, policy, _ = scenario(rng)
    target = rng.randrange(len(cases))
    case = cases[target]
    extraction = case.extraction.model_copy(update={"visible_text": f"{case.extraction.visible_text}\n{text}"})
    altered = [*cases[:target], case.model_copy(update={"extraction": extraction}), *cases[target + 1 :]]
    before = decide_all(cases, state, policy).decisions
    after = decide_all(altered, state, policy).decisions
    for old, new in zip(before, after, strict=True):
        if old.invoice_id == case.id:
            assert [r for r in new.rules if r.rule_id != "R2"] == [r for r in old.rules if r.rule_id != "R2"]
            assert not (old.agent_verdict is not AgentVerdict.PAY and new.agent_verdict is AgentVerdict.PAY)


@PROPERTY
@given(
    rng=st.randoms(use_true_random=False),
    field=st.sampled_from(["supplier_name", "amount", "currency", "account_number"]),
)
def test_a_value_without_a_verified_quote_is_never_paid_alone(rng: random.Random, field: str) -> None:
    cases, state, policy, _ = scenario(rng)
    unverified = []
    for case in cases:
        read = getattr(case.extraction, field).model_copy(update={"verified": False})
        unverified.append(case.model_copy(update={"extraction": case.extraction.model_copy(update={field: read})}))
    decisions = decide_all(unverified, state, policy).decisions
    assert all(d.agent_verdict is not AgentVerdict.PAY for d in decisions)
    assert all(d.rules[0].outcome is RuleOutcome.ESCALATE for d in decisions)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    return names | {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}


def test_the_engine_has_no_io_no_clock_no_randomness_and_no_model() -> None:
    forbidden = {"random", "time", "os", "io", "socket", "httpx", "anthropic", "custodio.llm", "custodio.config"}
    clock_calls = ("now", "today", "utcnow", "time_ns")
    for path in sorted(ENGINE.glob("*.py")):
        assert not _imports(path) & forbidden, path.name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        assert not calls & set(clock_calls), path.name
        names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert "open" not in names and "print" not in names, path.name


def test_only_metrics_reads_the_labels() -> None:
    readers = {
        path.name
        for path in ENGINE.glob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute) and node.attr in ("expected", "trap")
    }
    assert readers <= {"metrics.py"}
