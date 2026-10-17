"""The labelled demo dataset: every trap of the brief, decided at 100 % accuracy with zero improper payments."""

import re
from collections.abc import Callable
from decimal import Decimal

import pytest

from custodio.contracts import (
    AgentVerdict,
    Decision,
    DecisionStatus,
    InvoiceCase,
    InvoiceSource,
    RuleOutcome,
)
from custodio.dataset import demo_cases, demo_company, demo_specs
from custodio.engine import audit, decide, decide_all
from custodio.engine.rules import EVALUATORS, RuleContext, check

# Trap label in cases.json -> the rule that must catch it.
TRAPS = {
    "Cobro duplicado (mismo número)": "R5",
    "Cobro duplicado (otro número)": "R5",
    "Beneficiario nuevo": "R3",
    "Beneficiario bloqueado": "R3",
    "Suplantación de un proveedor conocido": "R3",
    "Cuenta cambiada": "R4",
    "No coincide con lo acordado (monto fijo)": "R6",
    "Supera el tope mensual acordado": "R6",
    "Sobre el límite por pago": "R10",
    "Sobre el tope de aprobación": "R9",
    "Cupo de pago automático agotado": "R11",
    "Saldo y reserva insuficientes": "R12",
    "Pago fraccionado": "R7",
    "Moneda no permitida": "R8",
    "Moneda ambigua": "R1",
    "Lectura de baja confianza": "R1",
    "Instrucción visible al agente": "R2",
    "Texto oculto dirigido al agente": "R2",
}


def golden() -> tuple[list[Decision], list[InvoiceCase]]:
    state, policy = demo_company()
    cases = demo_cases()
    return decide_all(cases, state, policy).decisions, cases


def test_the_demo_company_is_cobalto_labs_with_the_default_limits() -> None:
    state, policy = demo_company()
    assert state.company_name == "Cobalto Labs, Inc."
    assert (policy.approval_threshold, policy.per_payment_limit) == (Decimal(5000), Decimal(12000))
    assert (policy.period_budget, policy.reserve) == (Decimal(37000), Decimal(60000))
    assert len(policy.beneficiaries) >= 20
    assert any(not b.allowed for b in policy.beneficiaries)
    assert policy.approvers


def test_there_are_at_least_36_labelled_cases_with_unique_ids() -> None:
    cases = demo_cases()
    assert len(cases) >= 36
    assert len({case.id for case in cases}) == len(cases)
    assert all(case.expected is not None for case in cases)


def test_the_cases_cover_every_trap_and_variety_of_legitimate_invoices() -> None:
    cases = demo_cases()
    assert {case.trap for case in cases if case.trap} == set(TRAPS)
    legitimate = [case for case in cases if case.trap is None]
    assert all(case.expected == "pay" for case in legitimate)
    assert {case.extraction.currency.value for case in legitimate} >= {"USD", "COP", "MXN", "BRL"}
    assert {case.extraction.source for case in cases} >= {
        InvoiceSource.PDF,
        InvoiceSource.EMAIL,
        InvoiceSource.WHATSAPP,
        InvoiceSource.IMAGE,
    }


def test_specs_and_cases_describe_the_same_invoices() -> None:
    specs, cases = demo_specs(), demo_cases()
    assert len(specs) == len(cases)
    for spec, case in zip(specs, cases, strict=True):
        assert case.extraction.invoice_number.value == spec.invoice_number
        assert case.extraction.supplier_name.value == spec.supplier_name
        assert case.extraction.amount.value == f"{spec.amount:.2f}"
        assert bool(case.extraction.hidden_findings) == (spec.hidden_text is not None)


def test_every_read_value_is_backed_by_a_quote_found_in_the_document() -> None:
    for case in demo_cases():
        extraction = case.extraction
        for field in (extraction.supplier_name, extraction.amount, extraction.currency, extraction.account_number):
            assert field.verified and field.evidence is not None
            assert field.evidence.quote in extraction.visible_text


def test_the_golden_dataset_is_decided_at_100_percent_with_no_improper_payment() -> None:
    state, policy = demo_company()
    cases = demo_cases()
    batch = decide_all(cases, state, policy)
    labels = {case.id: case.expected for case in cases}
    wrong = [
        (d.invoice_id, d.agent_verdict.value) for d in batch.decisions if d.agent_verdict.value != labels[d.invoice_id]
    ]
    assert wrong == []
    assert batch.metrics.accuracy == 1.0
    assert batch.metrics.improper_payments == 0
    assert audit(batch, cases, state, policy).agrees
    assert batch.balance_end >= policy.reserve


@pytest.mark.parametrize("trap", sorted(TRAPS))
def test_each_trap_is_caught_by_its_rule(trap: str) -> None:
    decisions, cases = golden()
    trapped = {case.id for case in cases if case.trap == trap}
    for decision in (d for d in decisions if d.invoice_id in trapped):
        caught = next(r for r in decision.rules if r.rule_id == TRAPS[trap])
        assert caught.outcome in (RuleOutcome.HOLD, RuleOutcome.ESCALATE), caught.reason
        assert decision.status is not DecisionStatus.PAID_AUTO


def test_every_failed_rule_gives_a_spanish_reason_with_concrete_numbers() -> None:
    decisions, _ = golden()
    failed = [r for d in decisions for r in d.rules if r.outcome in (RuleOutcome.HOLD, RuleOutcome.ESCALATE)]
    assert failed
    assert [r.reason for r in failed if not re.search(r"\d", r.reason)] == []


def test_every_decision_has_an_explanation_and_every_stop_a_counterfactual() -> None:
    decisions, _ = golden()
    for decision in decisions:
        assert decision.explanation
        assert (decision.counterfactual is None) == (decision.agent_verdict is AgentVerdict.PAY)


def test_the_reserve_trap_leaves_room_for_a_smaller_payment_afterwards() -> None:
    decisions, cases = golden()
    reserve_trap = next(c.id for c in cases if c.trap == "Saldo y reserva insuficientes")
    later = [d for d in decisions[[d.invoice_id for d in decisions].index(reserve_trap) + 1 :]]
    assert any(d.status is DecisionStatus.PAID_AUTO for d in later)


SABOTAGES = {
    "R1": ("R1",),
    "R2": ("R2",),
    "R3": ("R3", "R4", "R6"),
    "R4": ("R4",),
    "R5": ("R5",),
    "R6": ("R6",),
    "R7": ("R7",),
    "R8": ("R8",),
    "R9": ("R9",),
    "R10": ("R9", "R10"),
    "R11": ("R11",),
    "R12": ("R12",),
}


def _always_pass(rule_id: str) -> Callable[[RuleContext], object]:
    return lambda context: check(rule_id, RuleOutcome.PASS, "Saboteada.")


@pytest.mark.parametrize("rule_id", sorted(SABOTAGES, key=lambda rule_id: int(rule_id[1:])))
def test_the_auditor_catches_every_sabotaged_rule_on_the_golden_dataset(
    rule_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    ignored = SABOTAGES[rule_id]
    sabotaged = {rid: _always_pass(rid) if rid in ignored else fn for rid, fn in EVALUATORS.items()}
    monkeypatch.setattr(decide, "EVALUATORS", sabotaged)
    state, policy = demo_company()
    cases = demo_cases()

    raw = decide.run_batch(cases, state, policy, approvals={}, vetoes={})
    assert audit(raw, cases, state, policy).improper_payments >= 1

    final = decide_all(cases, state, policy)
    assert final.metrics.improper_payments == 0
    trapped = {case.id for case in cases if case.trap and TRAPS[case.trap] == rule_id}
    assert all(d.status is not DecisionStatus.PAID_AUTO for d in final.decisions if d.invoice_id in trapped)
