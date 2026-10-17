from datetime import date
from decimal import Decimal

import pytest

from custodio.contracts import (
    RULES,
    AgentVerdict,
    AgreementKind,
    DecisionStatus,
    RuleOutcome,
    RuleResult,
)
from custodio.engine import decide, decide_all
from custodio.engine.decide import verdict_of
from custodio.engine.errors import DuplicateCaseIdError, EngineInvariantError
from custodio.engine.rules import EVALUATORS, check
from tests.engine.builders import (
    ANDES,
    agreement,
    approval,
    beneficiary,
    invoice,
    paid,
    policy,
    rule,
    squeezed_by_a_later_payment,
    state,
)

CAPPED = policy(beneficiary(deal=agreement("60000", kind=AgreementKind.MONTHLY_CAP)))


def results(*outcomes: RuleOutcome) -> list[RuleResult]:
    return [
        RuleResult(rule_id=spec.id, key=spec.key, label=spec.label, outcome=outcome, reason="x.")
        for spec, outcome in zip(RULES, outcomes, strict=True)
    ]


P, H, X, S = RuleOutcome.PASS, RuleOutcome.HOLD, RuleOutcome.ESCALATE, RuleOutcome.SKIPPED


def test_verdict_hold_beats_escalate_and_escalate_beats_pay() -> None:
    assert verdict_of(results(*[P] * 12)) is AgentVerdict.PAY
    assert verdict_of(results(X, *[P] * 11)) is AgentVerdict.ESCALATE
    assert verdict_of(results(X, P, P, H, *[P] * 8)) is AgentVerdict.HOLD


def test_a_rule_that_could_not_be_evaluated_never_lets_a_payment_through() -> None:
    assert verdict_of(results(*[P] * 11, S)) is AgentVerdict.ESCALATE


def test_hold_beats_escalate_in_a_real_decision() -> None:
    [decision] = decide_all([invoice(account="7788-9902", amount="9000.00")], state(), CAPPED).decisions
    assert rule(decision, "R4").outcome is H and rule(decision, "R9").outcome is X
    assert decision.agent_verdict is AgentVerdict.HOLD
    assert decision.status is DecisionStatus.HOLD


def test_a_payment_moves_the_balance_and_the_budget() -> None:
    history = paid("1000", on=date(2026, 10, 1), beneficiary_id="b9", number="Z-1")
    cases = [invoice("F-1", day=2, amount="2000.00", number="A-1"), invoice("F-2", day=3, amount="1500", number="A-2")]
    batch = decide_all(cases, state(history, balance="100000"), CAPPED)
    first, second = batch.decisions
    assert (first.status, second.status) == (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_AUTO)
    assert (first.balance_before, first.balance_after) == (Decimal(100000), Decimal(98000))
    assert (second.balance_before, second.balance_after) == (Decimal(98000), Decimal(96500))
    assert batch.balance_end == Decimal(96500)
    assert batch.spent_auto_base == Decimal(4500)


def test_a_decision_that_does_not_pay_leaves_the_balance_alone() -> None:
    [decision] = decide_all([invoice(account="7788-9902")], state(), policy()).decisions
    assert decision.balance_before == decision.balance_after == Decimal(140000)


def test_decision_carries_who_and_how_much() -> None:
    company = policy(beneficiary(currency="COP", deal=agreement("9200000", "COP")))
    [decision] = decide_all([invoice(amount="9200000", currency="COP")], state(), company).decisions
    assert decision.beneficiary_id == "b1"
    assert decision.supplier_name == "Andes Code SAS"
    assert (decision.amount, decision.currency) == (Decimal(9200000), "COP")
    assert decision.amount_base is not None and round(decision.amount_base, 2) == Decimal("2243.90")


def test_an_unknown_supplier_keeps_the_name_it_was_read_with() -> None:
    case = invoice(supplier="Orbit Growth Partners LLC", tax_id="61-5590147")
    [decision] = decide_all([case], state(), policy()).decisions
    assert decision.beneficiary_id is None and decision.supplier_name == "Orbit Growth Partners LLC"


def test_decisions_come_back_in_arrival_order() -> None:
    cases = [invoice("F-late", day=9, number="A-9"), invoice("F-early", day=2, number="A-2")]
    assert [d.invoice_id for d in decide_all(cases, state(), policy()).decisions] == ["F-early", "F-late"]


def test_two_cases_with_the_same_id_are_rejected() -> None:
    with pytest.raises(DuplicateCaseIdError):
        decide_all([invoice("F-1"), invoice("F-1", number="B")], state(), policy())


def test_deciding_twice_gives_the_same_result() -> None:
    cases = [invoice("F-1"), invoice("F-2", day=3, account="7788-9902", number="B")]
    assert decide_all(cases, state(), policy()) == decide_all(cases, state(), policy())


# Approvals ------------------------------------------------------------------------------------------------------


def test_an_approved_escalation_is_paid_by_a_person() -> None:
    case = invoice(amount="6500.00")
    batch = decide_all([case], state(), CAPPED, {"F-001": approval("F-001")})
    [decision] = batch.decisions
    assert decision.agent_verdict is AgentVerdict.ESCALATE
    assert decision.status is DecisionStatus.PAID_HUMAN
    assert decision.approval is not None and decision.approval.approver == "Ana Gómez"
    assert (decision.balance_before, decision.balance_after) == (Decimal(140000), Decimal(133500))
    assert batch.balance_end == Decimal(133500)
    assert batch.spent_auto_base == 0


def test_a_rejected_escalation_is_rejected() -> None:
    batch = decide_all([invoice(amount="6500.00")], state(), CAPPED, {"F-001": approval("F-001", approved=False)})
    assert batch.decisions[0].status is DecisionStatus.REJECTED
    assert batch.balance_end == Decimal(140000)


def test_an_approval_never_breaks_the_reserve() -> None:
    cases, money = squeezed_by_a_later_payment()
    batch = decide_all(cases, money, CAPPED, {"F-001": approval("F-001")})
    decision = batch.decisions[0]
    assert decision.agent_verdict is AgentVerdict.ESCALATE
    assert decision.status is DecisionStatus.HOLD
    assert decision.blocked_reason is not None
    assert "USD 59.500" in decision.blocked_reason and "USD 60.000" in decision.blocked_reason
    assert batch.balance_end == Decimal(66000)


def test_an_approval_cannot_lift_a_hold_rule() -> None:
    batch = decide_all([invoice(account="7788-9902")], state(), policy(), {"F-001": approval("F-001")})
    [decision] = batch.decisions
    assert decision.status is DecisionStatus.HOLD
    assert decision.approval is not None
    assert decision.blocked_reason is not None and "Cuenta registrada" in decision.blocked_reason


def test_an_approval_for_an_unknown_invoice_is_ignored() -> None:
    batch = decide_all([invoice()], state(), policy(), {"F-404": approval("F-404")})
    assert batch.decisions[0].status is DecisionStatus.PAID_AUTO


def test_approvals_are_applied_in_the_order_they_were_given() -> None:
    cases = [invoice("F-1", amount="6500.00", number="A-1"), invoice("F-2", amount="6000.00", number="A-2", day=2)]
    approvals = {"F-1": approval("F-1", minute=30), "F-2": approval("F-2", minute=5)}
    first, second = decide_all(cases, state(balance="72000"), CAPPED, approvals).decisions
    assert second.status is DecisionStatus.PAID_HUMAN
    assert first.status is DecisionStatus.HOLD and first.blocked_reason is not None


def test_approving_one_invoice_does_not_change_the_others() -> None:
    cases = [invoice("F-1", amount="6500.00", number="A-1"), invoice("F-2", day=2, amount="900.00", number="A-2")]
    before = decide_all(cases, state(), CAPPED)
    after = decide_all(cases, state(), CAPPED, {"F-1": approval("F-1")})
    assert after.decisions[1] == before.decisions[1]


# Metrics --------------------------------------------------------------------------------------------------------


def test_metrics_count_every_status() -> None:
    cases = [
        invoice("F-pay", day=1, number="A-1", amount="1000.00"),
        invoice("F-hold", day=5, number="A-2", account="7788-9902"),
        invoice("F-ask", day=9, number="A-3", amount="6500.00"),
        invoice("F-human", day=13, number="A-4", amount="7000.00"),
        invoice("F-no", day=17, number="A-5", amount="8000.00"),
    ]
    approvals = {"F-human": approval("F-human"), "F-no": approval("F-no", approved=False)}
    metrics = decide_all(cases, state(), CAPPED, approvals).metrics
    assert (metrics.total, metrics.paid_auto, metrics.hold, metrics.pending) == (5, 1, 1, 1)
    assert (metrics.paid_human, metrics.rejected) == (1, 1)
    assert metrics.autonomy_rate == pytest.approx(0.4)
    assert metrics.accuracy is None
    assert metrics.improper_payments == 0


def test_an_approval_blocked_by_the_reserve_is_not_counted_as_decided_alone() -> None:
    cases, money = squeezed_by_a_later_payment()
    metrics = decide_all(cases, money, CAPPED, {"F-001": approval("F-001")}).metrics
    assert (metrics.paid_auto, metrics.hold) == (1, 1)
    assert metrics.autonomy_rate == pytest.approx(0.5)


def test_accuracy_compares_the_agent_verdict_with_the_labels() -> None:
    right = invoice("F-1", number="A-1").model_copy(update={"expected": "pay"})
    wrong = invoice("F-2", day=10, number="A-2", account="7788-9902").model_copy(update={"expected": "escalate"})
    unlabelled = invoice("F-3", day=20, number="A-3", amount="900.00")
    assert decide_all([right, wrong, unlabelled], state(), CAPPED).metrics.accuracy == pytest.approx(0.5)


def test_an_empty_batch_has_zero_autonomy_and_no_accuracy() -> None:
    metrics = decide_all([], state(), policy()).metrics
    assert (metrics.total, metrics.autonomy_rate, metrics.accuracy) == (0, 0.0, None)


# Explanation and counterfactual ---------------------------------------------------------------------------------


def test_a_payment_is_explained_with_its_numbers_and_has_no_counterfactual() -> None:
    [decision] = decide_all([invoice()], state(), policy()).decisions
    assert decision.explanation.startswith("Se paga sola: se cumplen las 12 reglas.")
    for text in ("Andes Code SAS", "USD 4.800", "USD 5.000", "USD 135.200", "USD 60.000", "USD 37.000"):
        assert text in decision.explanation
    assert decision.counterfactual is None


def test_a_hold_is_explained_with_its_hold_reasons_first() -> None:
    [decision] = decide_all([invoice(account="7788-9902", amount="9000.00")], state(), CAPPED).decisions
    assert decision.explanation.startswith("Se retiene: no se paga.")
    assert "7788-9902" in decision.explanation
    assert "Además" in decision.explanation and "USD 5.000" in decision.explanation


def test_an_escalation_says_a_person_must_approve() -> None:
    [decision] = decide_all([invoice(amount="6500.00")], state(), CAPPED).decisions
    assert decision.explanation.startswith("Se pide aprobación a una persona.")
    assert decision.explanation.endswith("El agente no paga esto sin aprobación.")


def test_counterfactual_names_the_minimum_change_with_numbers() -> None:
    [decision] = decide_all([invoice(amount="6500.00")], state(), CAPPED).decisions
    assert decision.counterfactual is not None
    assert decision.counterfactual.startswith("Se habría pagado sola si ")
    assert "USD 5.000" in decision.counterfactual and "USD 6.500" in decision.counterfactual


def test_counterfactual_lists_every_failed_rule() -> None:
    [decision] = decide_all([invoice(account="7788-9902", amount="9000.00")], state(), CAPPED).decisions
    assert decision.counterfactual is not None
    assert "0012-4821" in decision.counterfactual and "USD 5.000" in decision.counterfactual


def test_the_explanation_records_the_person_who_decided() -> None:
    approvals = {"F-1": approval("F-1"), "F-2": approval("F-2", approved=False)}
    cases = [invoice("F-1", amount="6500.00", number="A-1"), invoice("F-2", amount="7000.00", number="A-2", day=4)]
    paid_by_person, rejected = decide_all(cases, state(), CAPPED, approvals).decisions
    assert "Ana Gómez lo aprobó el 16 de octubre" in paid_by_person.explanation
    assert "Ana Gómez lo rechazó el 16 de octubre" in rejected.explanation


def test_a_blocked_approval_is_explained() -> None:
    cases, money = squeezed_by_a_later_payment()
    batch = decide_all(cases, money, CAPPED, {"F-001": approval("F-001")})
    assert "Ana Gómez lo aprobó, pero no se paga" in batch.decisions[0].explanation


def test_history_for_another_beneficiary_does_not_touch_this_one() -> None:
    history = paid("4800", on=date(2026, 10, 1), beneficiary_id="b2", number="AC-2026-10")
    [decision] = decide_all([invoice()], state(history), policy(ANDES)).decisions
    assert rule(decision, "R5").outcome is P


def test_an_engine_bug_that_would_pay_without_an_amount_stops_instead(monkeypatch: pytest.MonkeyPatch) -> None:
    always_pass = {rule_id: (lambda context, r=rule_id: check(r, P, "Saboteada.")) for rule_id in EVALUATORS}
    monkeypatch.setattr(decide, "EVALUATORS", always_pass)
    with pytest.raises(EngineInvariantError):
        decide_all([invoice(amount=None)], state(), policy())
