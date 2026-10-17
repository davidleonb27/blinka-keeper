"""R9 reads the cap a supplier earned when it has one; without trust history nothing changes."""

from datetime import timedelta
from decimal import Decimal

from custodio.contracts import AgentVerdict, CompanyState, DecisionStatus, RuleOutcome, TrustCap
from custodio.dataset import demo_cases, demo_company
from custodio.dataset.demo import load_demo, to_case
from custodio.engine import audit, decide_all

ANDES = "b1"  # F-004, USD 4.800, paid alone under the policy's USD 5.000
RUTA_LEGAL = "b9"  # F-013, COP 26.650.000 (≈ USD 6.500), escalated only by R9


def with_trust(state: CompanyState, **caps: Decimal) -> CompanyState:
    trust = {
        supplier: TrustCap(beneficiary_id=supplier, cap=cap, clean_streak=3, supervised=cap == 0, reason="Por prueba.")
        for supplier, cap in caps.items()
    }
    return state.model_copy(update={"trust": trust})


def test_without_trust_history_the_demo_batch_decides_exactly_as_before() -> None:
    state, policy = demo_company()
    batch = decide_all(demo_cases(), state, policy)
    assert all(decision.trust is None for decision in batch.decisions)
    assert batch.metrics.accuracy == 1.0
    assert batch.metrics.improper_payments == 0
    r9 = next(rule for rule in batch.decisions[3].rules if rule.rule_id == "R9")
    assert r9.reason == "USD 4.800 está dentro del tope de aprobación automática de USD 5.000."


def test_a_supervised_supplier_is_escalated_by_r9_even_under_the_policy_threshold() -> None:
    state, policy = demo_company()
    batch = decide_all(demo_cases(), with_trust(state, **{ANDES: Decimal(0)}), policy)
    andes = next(d for d in batch.decisions if d.invoice_id == "F-004")
    r9 = next(rule for rule in andes.rules if rule.rule_id == "R9")
    assert andes.status is DecisionStatus.PENDING_APPROVAL
    assert r9.outcome is RuleOutcome.ESCALATE
    assert "Andes Code SAS" in r9.reason and "USD 0" in r9.reason
    assert andes.trust is not None and andes.trust.cap == Decimal(0)
    assert andes.counterfactual is not None and "recuperado la confianza" in andes.counterfactual


def test_an_earned_cap_above_the_threshold_lets_the_agent_pay_and_the_auditor_agrees() -> None:
    state, policy = demo_company()
    trusted = with_trust(state, **{RUTA_LEGAL: Decimal(8000)})
    batch = decide_all(demo_cases(), trusted, policy)
    ruta = next(d for d in batch.decisions if d.invoice_id == "F-013")
    assert ruta.agent_verdict is AgentVerdict.PAY
    assert ruta.status is DecisionStatus.PAID_AUTO
    assert ruta.trust is not None and ruta.trust.cap == Decimal(8000)
    r9 = next(rule for rule in ruta.rules if rule.rule_id == "R9")
    assert "USD 8.000 que Ruta Legal Abogados SAS se ha ganado" in r9.reason
    assert audit(batch, demo_cases(), trusted, policy).agrees


def test_the_auditor_rejects_a_payment_over_the_cap_the_supplier_earned() -> None:
    state, policy = demo_company()
    paid_alone = decide_all(demo_cases(), state, policy)
    report = audit(paid_alone, demo_cases(), with_trust(state, **{ANDES: Decimal(1000)}), policy)
    assert not report.agrees
    assert any(f.invoice_id == "F-004" and "tope de aprobación" in f.message for f in report.findings)


def test_a_risk_signal_supervises_the_supplier_for_the_rest_of_the_same_batch() -> None:
    demo = load_demo()
    state, policy = demo.state, demo.policy
    paredes = next(b for b in policy.beneficiaries if b.id == "b16")
    changed = next(case for case in demo.cases if case.id == "F-023")  # asks to pay another account (R4)
    legit = changed.model_copy(
        update={
            "id": "F-023b",
            "received_at": changed.received_at + timedelta(hours=2),
            "spec": changed.spec.model_copy(
                update={"account_number": paredes.account_number, "invoice_number": "AP-2026-11"}
            ),
        }
    )
    cases = [to_case(case, customer=state.company_name) for case in (changed, legit)]
    batch = decide_all(cases, with_trust(state, b16=Decimal(5000)), policy)
    first, second = batch.decisions
    assert first.status is DecisionStatus.HOLD
    assert second.status is DecisionStatus.PENDING_APPROVAL
    assert second.trust is not None and second.trust.cap == Decimal(0) and second.trust.supervised
    assert "F-023" in second.trust.reason
