"""The pure part of «Custodio sugiere»: which repeated approvals become a proposal, and what a proposal may touch."""

from datetime import UTC, datetime
from decimal import Decimal

from custodio.contracts import Agreement, AgreementKind, Beneficiary, Policy
from custodio.services.suggestion_service import (
    MAX_SUGGESTED_TOLERANCE_PCT,
    ApprovedException,
    propose,
)

HOSTING = Beneficiary(
    id="b8",
    name="Nube Austral SpA",
    tax_id="77.341.908-2",
    bank_name="Banco de Chile",
    account_number="0001-2049",
    currency="USD",
    agreement=Agreement(kind=AgreementKind.FIXED, amount=Decimal(2150), currency="USD"),
)
LEGAL = Beneficiary(
    id="b9",
    name="Ruta Legal",
    tax_id="900",
    bank_name="Banco",
    account_number="1",
    currency="COP",
    agreement=Agreement(kind=AgreementKind.MONTHLY_CAP, amount=Decimal(60_000_000), currency="COP"),
)
POLICY = Policy(beneficiaries=[HOSTING, LEGAL])


def approved(
    amount: str, *, beneficiary: str = "b8", rules: tuple[str, ...] = ("R6",), currency: str = "USD", n: int = 0
) -> ApprovedException:
    return ApprovedException(
        invoice_id=f"INV-{beneficiary}-{amount}-{n}",
        beneficiary_id=beneficiary,
        amount=Decimal(amount),
        currency=currency,
        failed_rules=rules,
        approver="Ana Gómez",
        approved_at=datetime(2026, 9, 1 + n, tzinfo=UTC),
        note="Subió el precio",
    )


def three_above(amounts: tuple[str, ...] = ("2236", "2232", "2239")) -> list[ApprovedException]:
    return [approved(amount, n=n) for n, amount in enumerate(amounts)]


def test_three_approvals_of_the_same_exception_make_one_proposal() -> None:
    [proposal] = propose(three_above(), POLICY, min_approvals=3)

    assert proposal.beneficiary.id == "b8"
    assert proposal.current_tolerance_pct == Decimal(2)
    assert proposal.proposed_tolerance_pct == Decimal(5)
    assert len(proposal.evidence) == 3
    assert "3 veces" in proposal.question
    assert "5 %" in proposal.question


def test_below_the_threshold_nothing_is_proposed() -> None:
    assert propose(three_above()[:2], POLICY, min_approvals=3) == []
    assert len(propose(three_above()[:2], POLICY, min_approvals=2)) == 1


def test_a_proposal_changes_only_that_supplier_tolerance() -> None:
    [proposal] = propose(three_above(), POLICY, min_approvals=3)

    proposed = proposal.proposed
    assert proposed.model_dump(exclude={"beneficiaries"}) == POLICY.model_dump(exclude={"beneficiaries"})
    assert proposed.beneficiaries[1] == LEGAL
    changed = proposed.beneficiaries[0]
    assert changed.model_dump(exclude={"agreement"}) == HOSTING.model_dump(exclude={"agreement"})
    assert HOSTING.agreement is not None and changed.agreement is not None
    assert changed.agreement.model_dump(exclude={"tolerance_pct"}) == HOSTING.agreement.model_dump(
        exclude={"tolerance_pct"}
    )
    assert [change.field for change in proposal.changes] == ["beneficiaries[b8].agreement.tolerance_pct"]


def test_approvals_of_hard_rules_never_become_a_proposal() -> None:
    for hard in ("R2", "R4", "R5", "R14"):
        approvals = [approved(a, rules=("R6", hard), n=n) for n, a in enumerate(("2236", "2232", "2239"))]
        assert propose(approvals, POLICY, min_approvals=3) == [], hard


def test_global_caps_are_never_proposed() -> None:
    approvals = [approved("2150", rules=(rule,), n=n) for n, rule in enumerate(("R9", "R10", "R11", "R12"))]
    assert propose(approvals * 3, POLICY, min_approvals=3) == []


def test_exceptions_beyond_the_largest_tolerance_custodio_proposes_are_left_to_people() -> None:
    far = three_above(("2700", "2710", "2720"))  # about 26 % above the agreement
    assert propose(far, POLICY, min_approvals=3) == []
    assert MAX_SUGGESTED_TOLERANCE_PCT <= Decimal(10)


def test_exceptions_already_inside_the_tolerance_are_not_counted() -> None:
    covered = Policy(
        beneficiaries=[
            HOSTING.model_copy(
                update={"agreement": HOSTING.agreement.model_copy(update={"tolerance_pct": Decimal(5)})}  # type: ignore[union-attr]
            )
        ]
    )
    assert propose(three_above(), covered, min_approvals=3) == []


def test_another_currency_or_a_monthly_cap_is_not_compared() -> None:
    other_currency = [approved(a, currency="EUR", n=n) for n, a in enumerate(("2236", "2232", "2239"))]
    monthly = [approved(a, beneficiary="b9", currency="COP", n=n) for n, a in enumerate(("1", "2", "3"))]
    assert propose(other_currency, POLICY, min_approvals=3) == []
    assert propose(monthly, POLICY, min_approvals=3) == []


def test_unknown_suppliers_are_ignored() -> None:
    ghost = [approved(a, beneficiary="ghost", n=n) for n, a in enumerate(("2236", "2232", "2239"))]
    assert propose(ghost, POLICY, min_approvals=3) == []


def test_the_proposal_id_is_stable_for_the_same_evidence() -> None:
    first = propose(three_above(), POLICY, min_approvals=3)[0].id
    again = propose(list(reversed(three_above())), POLICY, min_approvals=3)[0].id
    assert first == again
