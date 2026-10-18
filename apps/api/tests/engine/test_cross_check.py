"""R1 and the auditor with two independent readings: unless they agree on supplier, amount, currency and account,
nothing is paid alone."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from custodio.contracts import (
    AgentVerdict,
    CrossCheckStatus,
    DecisionStatus,
    FieldCrossCheck,
    InvoiceCase,
    ReaderValue,
    ReadingCrossCheck,
    RuleOutcome,
)
from custodio.engine import audit, decide_all
from tests.engine.builders import ANDES_ACCOUNT, invoice, policy, rule, state

FIRST, SECOND = "claude-sonnet-5-5", "gemini-2.5-flash"
CLEAN = {"supplier_name": "Andes Code SAS", "amount": "4800.00", "currency": "USD", "account_number": ANDES_ACCOUNT}


def comparison(field: str, first: str | None, second: str | None, *, agree: bool) -> FieldCrossCheck:
    return FieldCrossCheck.model_validate(
        {
            "field": field,
            "readings": [
                ReaderValue(reader=FIRST, value=first, quote=first),
                ReaderValue(reader=SECOND, value=second, quote=second),
            ],
            "agree": agree,
        }
    )


def checked(**second: str | None) -> ReadingCrossCheck:
    """The second reader gives CLEAN values except the ones passed; `agree` is what an honest comparer would say."""
    fields = [comparison(name, value, second.get(name, value), agree=name not in second) for name, value in CLEAN.items()]
    status = CrossCheckStatus.DISAGREE if second else CrossCheckStatus.AGREE
    return ReadingCrossCheck(status=status, fields=fields)


def with_check(cross_check: ReadingCrossCheck | None, case: InvoiceCase | None = None) -> InvoiceCase:
    base = case or invoice()
    extraction = base.extraction.model_copy(update={"cross_check": cross_check})
    return base.model_copy(update={"extraction": extraction})


def decided(case: InvoiceCase) -> tuple[AgentVerdict, str]:
    [decision] = decide_all([case], state(), policy()).decisions
    return decision.agent_verdict, rule(decision, "R1").reason


def test_two_readings_that_agree_pay_and_say_so() -> None:
    verdict, reason = decided(with_check(checked()))
    assert verdict is AgentVerdict.PAY
    assert "Las dos lecturas independientes coinciden" in reason


def test_without_a_cross_check_r1_behaves_as_before() -> None:
    verdict, reason = decided(with_check(None))
    assert verdict is AgentVerdict.PAY and "lecturas" not in reason


def test_an_amount_disagreement_escalates_with_both_amounts_in_latin_format() -> None:
    verdict, reason = decided(with_check(checked(amount="48000.00")))
    assert verdict is AgentVerdict.ESCALATE
    assert "Las dos lecturas no coinciden en el monto: 4.800,00 vs 48.000,00." in reason


@pytest.mark.parametrize(
    ("field", "other", "label"),
    [
        ("supplier_name", "Andes Kode SAS", "el proveedor: Andes Code SAS vs Andes Kode SAS"),
        ("currency", "COP", "la moneda: USD vs COP"),
        ("account_number", "4471-0098-12", f"la cuenta: {ANDES_ACCOUNT} vs 4471-0098-12"),
        ("amount", "4.80", "el monto: 4.800,00 vs 4,80"),
    ],
)
def test_every_compared_field_escalates_on_disagreement(field: str, other: str, label: str) -> None:
    verdict, reason = decided(with_check(checked(**{field: other})))
    assert verdict is AgentVerdict.ESCALATE
    assert f"Las dos lecturas no coinciden en {label}" in reason


def test_a_value_only_one_reader_stated_is_a_disagreement() -> None:
    verdict, reason = decided(with_check(checked(account_number=None)))
    assert verdict is AgentVerdict.ESCALATE and "(sin leer)" in reason


def test_several_disagreements_are_all_named() -> None:
    _, reason = decided(with_check(checked(amount="480.00", currency="EUR")))
    assert "el monto: 4.800,00 vs 480,00" in reason and "la moneda: USD vs EUR" in reason


def test_a_second_reading_that_failed_escalates_with_its_reason() -> None:
    unavailable = ReadingCrossCheck(status=CrossCheckStatus.UNAVAILABLE, error="el segundo lector no respondió")
    verdict, reason = decided(with_check(unavailable))
    assert verdict is AgentVerdict.ESCALATE
    assert "No hubo segunda lectura independiente (el segundo lector no respondió)" in reason


def test_an_agree_status_with_a_field_marked_in_disagreement_still_escalates() -> None:
    forged = checked(amount="48000.00").model_copy(update={"status": CrossCheckStatus.AGREE})
    verdict, _ = decided(with_check(forged))
    assert verdict is AgentVerdict.ESCALATE


def test_an_agree_status_with_fields_missing_still_escalates() -> None:
    verdict, _ = decided(with_check(ReadingCrossCheck(status=CrossCheckStatus.AGREE, fields=[])))
    assert verdict is AgentVerdict.ESCALATE


# The auditor recomputes agreement from the raw values, not from the flags -----------------------------------------


@pytest.mark.parametrize(
    "cross_check",
    [
        checked(amount="48000.00"),
        checked(account_number="9999").model_copy(update={"status": CrossCheckStatus.AGREE}),
        ReadingCrossCheck(
            status=CrossCheckStatus.AGREE,
            fields=[comparison(name, value, "otro", agree=True) for name, value in CLEAN.items()],
        ),
        ReadingCrossCheck(status=CrossCheckStatus.UNAVAILABLE, error="sin presupuesto"),
    ],
)
def test_a_forged_payment_over_readings_that_disagree_is_improper(cross_check: ReadingCrossCheck) -> None:
    case = with_check(cross_check)
    honest = decide_all([case], state(), policy())
    forged_decisions = [d.model_copy(update={"status": DecisionStatus.PAID_AUTO}) for d in honest.decisions]
    report = audit(honest.model_copy(update={"decisions": forged_decisions}), [case], state(), policy())
    assert report.improper_payments == 1
    assert "lecturas" in report.findings[0].message


def test_the_auditor_accepts_readings_that_agree_after_normalization() -> None:
    normalized = ReadingCrossCheck(
        status=CrossCheckStatus.AGREE,
        fields=[
            comparison("supplier_name", "Andes Code SAS", "ANDES  CODE S.A.S.", agree=True),
            comparison("amount", "4800.00", "4800.0", agree=True),
            comparison("currency", "USD", "usd", agree=True),
            comparison("account_number", ANDES_ACCOUNT, ANDES_ACCOUNT.replace("-", " "), agree=True),
        ],
    )
    case = with_check(normalized)
    batch = decide_all([case], state(), policy())
    assert batch.decisions[0].status is DecisionStatus.PAID_AUTO
    assert audit(batch, [case], state(), policy()).agrees


# No combination of readings in disagreement is ever paid alone ---------------------------------------------------

_OTHER_VALUES = {
    "supplier_name": st.sampled_from(["Andes Kode SAS", "Orbit Growth Partners LLC", ""]),
    "amount": st.decimals(min_value=Decimal("0.01"), max_value=Decimal("99999"), places=2).map(str),
    "currency": st.sampled_from(["COP", "EUR", "MXN", "BRL"]),
    "account_number": st.from_regex(r"[0-9]{4}-[0-9]{4}-[0-9]{2}", fullmatch=True),
}


@st.composite
def disagreements(draw: st.DrawFn) -> dict[str, str | None]:
    names = draw(st.lists(st.sampled_from(sorted(CLEAN)), min_size=1, max_size=4, unique=True))
    values = {name: draw(st.one_of(st.none(), _OTHER_VALUES[name])) for name in names}
    return {name: value for name, value in values.items() if value != CLEAN[name]} or {"amount": None}


@given(disagreements(), st.sampled_from(list(CrossCheckStatus)), st.booleans())
def test_no_disagreement_is_ever_paid_alone(
    second: dict[str, str | None], claimed: CrossCheckStatus, flags_lie: bool
) -> None:
    honest = checked(**second)
    fields = [f.model_copy(update={"agree": True}) for f in honest.fields] if flags_lie else honest.fields
    case = with_check(ReadingCrossCheck(status=claimed, fields=fields))
    batch = decide_all([case], state(), policy())
    assert batch.decisions[0].status is not DecisionStatus.PAID_AUTO
    assert rule(batch.decisions[0], "R1").outcome is RuleOutcome.ESCALATE
