from decimal import Decimal

from custodio.contracts import AgreementKind, DecisionStatus
from custodio.engine import simulate
from tests.engine.builders import agreement, beneficiary, invoice, policy, state

CAPPED = policy(beneficiary(deal=agreement("60000", kind=AgreementKind.MONTHLY_CAP)))
CASES = [
    invoice("F-1", day=1, number="A-1", amount="6500.00"),
    invoice("F-2", day=5, number="A-2", amount="1000.00"),
    invoice("F-3", day=9, number="A-3", account="7788-9902"),
]


def test_the_same_policy_changes_nothing() -> None:
    report = simulate(CASES, state(), CAPPED, CAPPED)
    assert report.changed == []
    assert report.before == report.after


def test_raising_the_approval_threshold_lets_the_agent_pay_more() -> None:
    looser = CAPPED.model_copy(update={"approval_threshold": Decimal("7000")})
    report = simulate(CASES, state(), CAPPED, looser)
    [change] = report.changed
    assert (change.invoice_id, change.supplier_name) == ("F-1", "Andes Code SAS")
    assert (change.before, change.after) == (DecisionStatus.PENDING_APPROVAL, DecisionStatus.PAID_AUTO)
    assert change.reason.startswith("Con la política nueva se paga sola")
    assert (report.before.paid_auto, report.after.paid_auto) == (1, 2)


def test_lowering_the_threshold_says_which_rule_now_stops_it() -> None:
    stricter = CAPPED.model_copy(update={"approval_threshold": Decimal("900")})
    [change] = simulate(CASES, state(), CAPPED, stricter).changed
    assert change.invoice_id == "F-2"
    assert change.after is DecisionStatus.PENDING_APPROVAL
    assert "USD 1.000" in change.reason and "USD 900" in change.reason
