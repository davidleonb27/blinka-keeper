"""R13-R15 on the labelled dataset: the demo's registered data is valid, and each new trap is caught by its control.

The sanctions case lives only here, against the fictitious list of the tests: the public demo never carries the name
of a real sanctioned person or entity.
"""

import json
from pathlib import Path

from custodio.contracts import AgentVerdict, Beneficiary, Decision, RuleOutcome
from custodio.dataset import demo_cases, demo_company
from custodio.dataset.demo import DemoCase, to_case
from custodio.engine import audit, decide_all
from custodio.engine.bank_details import account_checks, tax_id_check
from custodio.engine.sanctions import SanctionsList

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sanctions"
FICTITIOUS = SanctionsList.from_json((FIXTURES / "fictitious_sdn.json").read_text(encoding="utf-8"))


def decided(case_id: str) -> Decision:
    state, policy = demo_company()
    return next(d for d in decide_all(demo_cases(), state, policy).decisions if d.invoice_id == case_id)


def outcome(decision: Decision, rule_id: str) -> tuple[RuleOutcome, str]:
    result = next(r for r in decision.rules if r.rule_id == rule_id)
    return result.outcome, result.reason


def test_every_registered_tax_id_and_account_of_the_demo_passes_its_check() -> None:
    _, policy = demo_company()
    problems = [
        check.problem
        for b in policy.beneficiaries
        for check in (
            tax_id_check(b.tax_id, country=b.country),
            *account_checks(b.account_number, currency=b.currency, country=b.country),
        )
        if check is not None and check.problem is not None
    ]
    assert problems == []


def test_the_demo_registers_a_domain_for_every_company_and_a_contact_for_the_suppliers_it_verifies() -> None:
    _, policy = demo_company()
    companies = [b for b in policy.beneficiaries if b.tax_id[0] in "89" or b.country in ("US", "DE")]
    assert companies and all(b.email_domain for b in companies if b.allowed)
    assert {"b12", "b16", "b29"} <= {b.id for b in policy.beneficiaries if b.approver_contact}


def test_the_mistyped_clabe_is_held_and_r13_names_the_expected_check_digit() -> None:
    decision = decided("F-037")
    assert decision.agent_verdict is AgentVerdict.HOLD
    r13, reason = outcome(decision, "R13")
    assert r13 is RuleOutcome.ESCALATE
    assert "La CLABE 072180001234567893 no pasa el dígito de control: esperado 7, viene 3" in reason


def test_the_lookalike_domain_with_a_new_account_points_to_the_registered_contact_only() -> None:
    decision = decided("F-038")
    assert decision.agent_verdict is AgentVerdict.HOLD
    r15, reason = outcome(decision, "R15")
    assert r15 is RuleOutcome.ESCALATE
    assert "joaquinrnendez.dev no es joaquinmendez.dev (homóglifos (rn por m))" in reason
    _, policy = demo_company()
    contact = next(b.approver_contact for b in policy.beneficiaries if b.id == "b12")
    assert contact is not None and contact in reason
    assert "0199" not in reason  # the phone the invoice offers is never the one to call
    assert "últimos 4 dígitos de la cuenta nueva (…4417)" in reason


def test_a_changed_account_in_the_demo_always_asks_for_out_of_band_verification() -> None:
    state, policy = demo_company()
    for decision in decide_all(demo_cases(), state, policy).decisions:
        r4, _ = outcome(decision, "R4")
        if r4 is RuleOutcome.HOLD:
            r15, reason = outcome(decision, "R15")
            assert r15 is RuleOutcome.ESCALATE and "No use ningún teléfono, correo ni enlace" in reason


def test_no_demo_supplier_hits_the_real_ofac_copy() -> None:
    state, policy = demo_company()
    hits = [
        d.invoice_id
        for d in decide_all(demo_cases(), state, policy).decisions
        if outcome(d, "R14")[0] is not RuleOutcome.PASS
    ]
    assert hits == []


def test_a_supplier_on_the_fictitious_list_is_escalated_by_r14_alone_and_the_rest_stays_at_100_percent() -> None:
    fixture = json.loads((FIXTURES / "sanctioned_case.json").read_text(encoding="utf-8"))
    state, policy = demo_company()
    policy = policy.model_copy(
        update={"beneficiaries": [*policy.beneficiaries, Beneficiary.model_validate(fixture["beneficiary"])]}
    )
    listed = to_case(DemoCase.model_validate(fixture["case"]), customer=state.company_name)
    cases = [*demo_cases(), listed]

    batch = decide_all(cases, state, policy, sanctions=FICTITIOUS)
    decision = next(d for d in batch.decisions if d.invoice_id == listed.id)
    assert decision.agent_verdict is AgentVerdict.ESCALATE
    assert [r.rule_id for r in decision.rules if r.outcome is not RuleOutcome.PASS] == ["R14"]
    r14, reason = outcome(decision, "R14")
    assert "QUIMERA FICTICIA TRADING LLC" in reason and "lista ficticia de prueba" in reason
    assert batch.metrics.accuracy == 1.0 and batch.metrics.improper_payments == 0
    assert audit(batch, cases, state, policy, sanctions=FICTITIOUS).agrees
