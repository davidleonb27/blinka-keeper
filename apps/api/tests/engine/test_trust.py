"""Earned autonomy: the cap each supplier earns is a pure fold of its trust history, bounded by the policy."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from hypothesis import given, settings
from hypothesis import strategies as st

from custodio.contracts import (
    RULES,
    AgentVerdict,
    Approval,
    Decision,
    DecisionStatus,
    LedgerKind,
    Policy,
    RuleOutcome,
    RuleResult,
    TrustPolicy,
)
from custodio.engine.ledger import next_entry
from custodio.engine.trust import (
    CLEAN_PAYMENTS_TO_EARN,
    TrustEvent,
    TrustEventKind,
    TrustTerms,
    classify,
    earned_cap,
    events_from_ledger,
    fold,
    next_step,
    terms_for,
    trust_cap,
)

AT = datetime(2026, 10, 17, 15, tzinfo=UTC)
TERMS = TrustTerms(floor=Decimal(0), ceiling=Decimal(12000), start=Decimal(5000), base_currency="USD")


def clean(amount: str, invoice_id: str = "F-1") -> TrustEvent:
    return TrustEvent(TrustEventKind.CLEAN, "b1", invoice_id, Decimal(amount), "Aprobado sin incidentes.")


def incident(rule_id: str = "R4", invoice_id: str = "F-9") -> TrustEvent:
    return TrustEvent(TrustEventKind.INCIDENT, "b1", invoice_id, None, "Cuenta cambiada.", rule_id=rule_id)


def decision(
    *,
    status: DecisionStatus = DecisionStatus.PAID_HUMAN,
    failing: dict[str, RuleOutcome] | None = None,
    approval: Literal["approved", "rejected"] | None = "approved",
    beneficiary_id: str | None = "b1",
) -> Decision:
    failing = failing or {}
    rules = [
        RuleResult(
            rule_id=spec.id,
            key=spec.key,
            label=spec.label,
            outcome=failing.get(spec.id, RuleOutcome.PASS),
            reason=f"Razón de {spec.id}.",
        )
        for spec in RULES
    ]
    given_approval = (
        Approval(invoice_id="F-1", decision=approval, approver="Ana Gómez", channel="web", at=AT) if approval else None
    )
    return Decision(
        invoice_id="F-1",
        beneficiary_id=beneficiary_id,
        supplier_name="Andes Code SAS",
        amount=Decimal(4800),
        currency="USD",
        amount_base=Decimal(4800),
        agent_verdict=AgentVerdict.ESCALATE,
        status=status,
        rules=rules,
        explanation="",
        counterfactual=None,
        approval=given_approval,
    )


# The formula ---------------------------------------------------------------------------------------------------


def test_a_supplier_without_history_keeps_the_policy_threshold() -> None:
    envelope = fold([], TERMS)
    assert envelope.cap == Decimal(5000)
    assert envelope.clean_streak == 0
    assert not envelope.supervised


def test_an_incident_sends_the_supplier_back_to_the_floor() -> None:
    envelope = fold([clean("4800"), incident()], TERMS)
    assert envelope.cap == Decimal(0)
    assert envelope.supervised
    assert envelope.last_incident is not None and envelope.last_incident.rule_id == "R4"


def test_a_supervised_supplier_earns_its_cap_after_three_clean_payments() -> None:
    history = [incident(), clean("900"), clean("1000")]
    assert fold(history, TERMS).cap == Decimal(0)
    earned = fold([*history, clean("1100")], TERMS)
    assert earned.cap == Decimal(1000)  # the median of the three, times 1
    assert not earned.supervised


def test_each_clean_payment_after_that_adds_a_quarter_of_the_median_up_to_twice_it() -> None:
    history = [incident(), *(clean("1000", f"F-{n}") for n in range(3))]
    caps = [fold(history + [clean("1000")] * extra, TERMS).cap for extra in range(7)]
    assert caps == [Decimal(n) for n in (1000, 1250, 1500, 1750, 2000, 2000, 2000)]


def test_an_earned_cap_can_go_above_the_global_threshold_but_never_above_the_ceiling() -> None:
    history = [clean("7000", f"F-{n}") for n in range(8)]
    assert fold(history, TERMS).cap == Decimal(12000)
    hard = TrustTerms(floor=Decimal(0), ceiling=Decimal(5000), start=Decimal(5000), base_currency="USD")
    assert fold(history, hard).cap == Decimal(5000)


def test_a_clean_payment_never_lowers_the_cap_of_a_supplier_that_never_had_an_incident() -> None:
    assert fold([clean("200")], TERMS).cap == Decimal(5000)


def test_the_earned_cap_is_rounded_down_to_the_cent() -> None:
    assert earned_cap(CLEAN_PAYMENTS_TO_EARN + 1, Decimal("333.335"), TERMS) == Decimal("416.66")


def test_terms_come_from_the_policy() -> None:
    policy = Policy(approval_threshold=Decimal(5000), per_payment_limit=Decimal(12000))
    assert terms_for(policy) == TrustTerms(Decimal(0), Decimal(12000), Decimal(5000), "USD")
    hard = policy.model_copy(update={"trust": TrustPolicy(floor=Decimal(500), hard_ceiling=True)})
    assert terms_for(hard) == TrustTerms(Decimal(500), Decimal(5000), Decimal(5000), "USD")


def test_a_floor_above_the_ceiling_is_held_at_the_ceiling() -> None:
    policy = Policy(approval_threshold=Decimal(5000), trust=TrustPolicy(floor=Decimal(9000), hard_ceiling=True))
    assert terms_for(policy).floor == Decimal(5000)


# The next step -------------------------------------------------------------------------------------------------


def test_the_next_step_of_a_supervised_supplier_says_how_many_clean_payments_it_needs() -> None:
    step = next_step(fold([incident(), clean("1000")], TERMS), TERMS)
    assert step.clean_needed == 2
    assert step.cap == Decimal(1000)


def test_a_supplier_supervised_with_no_payments_yet_has_no_amount_to_project() -> None:
    step = next_step(fold([incident()], TERMS), TERMS)
    assert (step.clean_needed, step.cap) == (3, None)


def test_the_next_step_of_an_earning_supplier_is_one_clean_payment_away() -> None:
    history = [incident(), *(clean("1000", f"F-{n}") for n in range(3))]
    step = next_step(fold(history, TERMS), TERMS)
    assert (step.clean_needed, step.cap) == (1, Decimal(1250))


# What counts as clean or as an incident ------------------------------------------------------------------------


def test_a_payment_a_person_approved_with_no_risk_signal_is_clean() -> None:
    event = classify(decision(failing={"R9": RuleOutcome.ESCALATE}))
    assert event is not None and event.kind is TrustEventKind.CLEAN
    assert event.amount_base == Decimal(4800)


def test_every_risk_signal_is_an_incident_even_when_a_person_approved() -> None:
    for rule_id in ("R2", "R4", "R5", "R6"):
        outcome = RuleOutcome.HOLD if rule_id in ("R4", "R5") else RuleOutcome.ESCALATE
        status = DecisionStatus.HOLD if outcome is RuleOutcome.HOLD else DecisionStatus.PAID_HUMAN
        event = classify(decision(status=status, failing={rule_id: outcome}))
        assert event is not None and event.kind is TrustEventKind.INCIDENT
        assert event.rule_id == rule_id
        assert event.reason == f"Razón de {rule_id}."


def test_a_rejection_is_an_incident() -> None:
    event = classify(decision(status=DecisionStatus.REJECTED, approval="rejected"))
    assert event is not None and event.kind is TrustEventKind.INCIDENT
    assert event.rule_id is None
    assert "Ana Gómez rechazó" in event.reason


def test_nothing_is_learned_from_a_payment_the_agent_made_alone_or_from_an_unknown_supplier() -> None:
    assert classify(decision(status=DecisionStatus.PAID_AUTO, approval=None)) is None
    assert classify(decision(status=DecisionStatus.PENDING_APPROVAL, approval=None)) is None
    assert classify(decision(beneficiary_id=None, failing={"R4": RuleOutcome.HOLD})) is None


# From the ledger -----------------------------------------------------------------------------------------------


def test_the_events_are_read_back_from_the_ledger_by_supplier_and_in_order() -> None:
    first = next_entry(
        None,
        kind=LedgerKind.TRUST_REVOKED,
        subject_id="b1",
        payload={"beneficiary_id": "b1", "invoice_id": "F-9", "rule_id": "R4", "reason": "Cuenta cambiada."},
        at=AT,
    )
    second = next_entry(first, kind=LedgerKind.DECISION, subject_id="F-2", payload={"status": "paid_auto"}, at=AT)
    third = next_entry(
        second,
        kind=LedgerKind.TRUST_RAISED,
        subject_id="b1",
        payload={"beneficiary_id": "b1", "invoice_id": "F-3", "amount_base": "1000", "reason": "Aprobado."},
        at=AT,
    )
    events = events_from_ledger([first, second, third])
    assert list(events) == ["b1"]
    assert [(e.kind, e.invoice_id, e.amount_base, e.seq) for e in events["b1"]] == [
        (TrustEventKind.INCIDENT, "F-9", None, 1),
        (TrustEventKind.CLEAN, "F-3", Decimal(1000), 3),
    ]


def test_the_cap_given_to_the_engine_explains_itself() -> None:
    supervised = trust_cap(fold([incident(), clean("1000")], TERMS), TERMS, "b1")
    assert supervised.cap == Decimal(0)
    assert supervised.supervised
    assert "1 de 3 pagos limpios" in supervised.reason
    earned = trust_cap(fold([incident(), clean("900"), clean("1000"), clean("1100")], TERMS), TERMS, "b1")
    assert "3 pagos limpios seguidos" in earned.reason
    assert "USD 1.000" in earned.reason


# Properties ----------------------------------------------------------------------------------------------------

amounts = st.decimals(min_value=Decimal("0.01"), max_value=Decimal(50000), places=2)
events = st.lists(
    st.one_of(amounts.map(lambda amount: clean(str(amount))), st.sampled_from(["R2", "R4", "R5", "R6"]).map(incident)),
    max_size=40,
)
money = st.decimals(min_value=Decimal(0), max_value=Decimal(30000), places=2)


@st.composite
def terms(draw: st.DrawFn) -> TrustTerms:
    floor, start, ceiling = sorted((draw(money), draw(money), draw(money)))
    return TrustTerms(floor=floor, ceiling=ceiling, start=start, base_currency="USD")


PROPERTY = settings(max_examples=300, deadline=None)


@PROPERTY
@given(events, terms())
def test_the_cap_never_leaves_the_floor_to_ceiling_band(history: list[TrustEvent], bounds: TrustTerms) -> None:
    for n in range(len(history) + 1):
        cap = fold(history[:n], bounds).cap
        assert bounds.floor <= cap <= bounds.ceiling


@PROPERTY
@given(events, terms())
def test_an_incident_always_drops_the_cap_to_the_floor_and_never_raises_it(
    history: list[TrustEvent], bounds: TrustTerms
) -> None:
    for n, event in enumerate(history):
        before, after = fold(history[:n], bounds), fold(history[: n + 1], bounds)
        if event.kind is TrustEventKind.INCIDENT:
            assert after.cap == bounds.floor
            assert after.cap <= before.cap


@PROPERTY
@given(events, terms())
def test_a_clean_payment_never_lowers_the_cap(history: list[TrustEvent], bounds: TrustTerms) -> None:
    for n, event in enumerate(history):
        if event.kind is TrustEventKind.CLEAN:
            assert fold(history[: n + 1], bounds).cap >= fold(history[:n], bounds).cap


@PROPERTY
@given(events, terms())
def test_the_fold_is_deterministic(history: list[TrustEvent], bounds: TrustTerms) -> None:
    assert fold(history, bounds) == fold(list(history), bounds)
