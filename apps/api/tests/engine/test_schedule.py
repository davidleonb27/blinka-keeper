"""When to pay what is already approved: on the due date, earlier only to earn a discount, never into the reserve."""

from datetime import date, timedelta
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from custodio.contracts import EarlyPaymentDiscount
from custodio.engine.schedule import (
    Obligation,
    Timing,
    Treasury,
    captured_value,
    plan,
    projected_balance,
    settled,
)

TODAY = date(2026, 10, 17)
TREASURY = Treasury(today=TODAY, cash=Decimal(100000), reserve=Decimal(60000), apy=Decimal("4.0"), base_currency="USD")


def obligation(
    invoice_id: str = "F-1",
    *,
    amount: str = "3650",
    due: date | None = date(2026, 11, 16),
    issued: date | None = date(2026, 10, 15),
    approved: date = TODAY,
    discount: EarlyPaymentDiscount | None = None,
    late_fee_pct: str | None = None,
    critical: bool = False,
) -> Obligation:
    return Obligation(
        invoice_id=invoice_id,
        beneficiary_id="b1",
        supplier_name=f"Proveedor {invoice_id}",
        amount=Decimal(amount),
        currency="USD",
        amount_base=Decimal(amount),
        approved_on=approved,
        issue_date=issued,
        due_date=due,
        discount=discount,
        late_fee_pct=Decimal(late_fee_pct) if late_fee_pct else None,
        critical=critical,
    )


def test_a_payment_goes_out_on_its_due_date_and_not_before() -> None:
    [planned] = plan([obligation()], TREASURY)
    assert planned.pay_on == date(2026, 11, 16)
    assert planned.timing is Timing.ON_DUE
    # USD 3.650 kept 30 more days at 4 % a year.
    assert planned.yield_base == Decimal("12.00")
    assert "16 de noviembre" in planned.reason
    assert "no antes" in planned.reason


def test_an_early_payment_discount_worth_more_than_the_yield_pays_on_its_last_day() -> None:
    terms = EarlyPaymentDiscount(percent=Decimal(2), days=10)
    [planned] = plan([obligation(discount=terms, issued=date(2026, 10, 15))], TREASURY)
    assert planned.pay_on == date(2026, 10, 25)
    assert planned.timing is Timing.DISCOUNT
    assert planned.discount_base == Decimal("73.00")
    assert "2 %" in planned.reason and "USD 73" in planned.reason


def test_a_discount_smaller_than_the_yield_of_waiting_is_left_alone() -> None:
    tiny = EarlyPaymentDiscount(percent=Decimal("0.01"), days=10)
    [planned] = plan([obligation(discount=tiny)], TREASURY)
    assert planned.timing is Timing.ON_DUE
    assert planned.discount_base == 0


def test_an_expired_discount_is_not_taken() -> None:
    terms = EarlyPaymentDiscount(percent=Decimal(2), days=10)
    [planned] = plan([obligation(discount=terms, issued=date(2026, 9, 1))], TREASURY)
    assert planned.timing is Timing.ON_DUE


def test_an_overdue_payment_or_one_without_a_due_date_goes_out_today() -> None:
    planned = plan([obligation("F-1", due=date(2026, 10, 10)), obligation("F-2", due=None)], TREASURY)
    overdue, undated = sorted(planned, key=lambda p: p.obligation.invoice_id)
    assert (overdue.pay_on, overdue.timing) == (TODAY, Timing.OVERDUE)
    assert "Venció el 10 de octubre" in overdue.reason
    assert (undated.pay_on, undated.timing) == (TODAY, Timing.NO_DUE_DATE)


def test_paying_by_the_due_date_avoids_the_agreed_late_fee() -> None:
    [planned] = plan([obligation(late_fee_pct="1.5")], TREASURY)
    assert planned.late_fee_avoided_base == Decimal("54.75")
    assert "mora" in planned.reason


def test_when_the_cash_does_not_reach_late_fees_then_critical_suppliers_go_first() -> None:
    short = Treasury(today=TODAY, cash=Decimal(66000), reserve=Decimal(60000), apy=Decimal(4), base_currency="USD")
    planned = plan(
        [
            obligation("F-plain", amount="3000", due=date(2026, 10, 20)),
            obligation("F-critical", amount="3000", due=date(2026, 10, 30), critical=True),
            obligation("F-late-fee", amount="3000", due=date(2026, 11, 5), late_fee_pct="2"),
        ],
        short,
    )
    by_id = {p.obligation.invoice_id: p for p in planned}
    assert by_id["F-late-fee"].pay_on == date(2026, 11, 5)
    assert by_id["F-critical"].pay_on == date(2026, 10, 30)
    assert by_id["F-plain"].pay_on is None
    assert by_id["F-plain"].timing is Timing.SHORT_OF_CASH
    assert "reserva de USD 60.000" in by_id["F-plain"].reason


def test_the_plan_is_in_payment_order_with_what_waits_for_cash_last() -> None:
    short = Treasury(today=TODAY, cash=Decimal(64000), reserve=Decimal(60000), apy=Decimal(4), base_currency="USD")
    planned = plan(
        [
            obligation("F-3", amount="3000", due=date(2026, 11, 5)),
            obligation("F-1", amount="1000", due=date(2026, 10, 20)),
            obligation("F-2", amount="3000", due=date(2026, 10, 25)),
        ],
        short,
    )
    assert [p.obligation.invoice_id for p in planned] == ["F-1", "F-2", "F-3"]
    assert planned[-1].pay_on is None


def test_the_projected_balance_falls_on_each_payment_day_and_stays_at_or_above_the_reserve() -> None:
    planned = plan([obligation("F-1", amount="1000", due=date(2026, 10, 20))], TREASURY)
    points = projected_balance(planned, TREASURY, horizon_days=5)
    assert [(p.day, p.balance) for p in points] == [
        (TODAY + timedelta(days=n), Decimal(100000) if n < 3 else Decimal(99000)) for n in range(6)
    ]


def test_a_settled_payment_is_valued_by_the_day_it_went_out() -> None:
    terms = EarlyPaymentDiscount(percent=Decimal(2), days=10)
    early = settled(obligation(discount=terms, approved=date(2026, 10, 15)), date(2026, 10, 20), TREASURY)
    assert early.timing is Timing.DISCOUNT
    assert early.discount_base == Decimal("73.00")
    assert early.yield_base == Decimal("2.00")


def test_the_value_captured_in_a_month_adds_discounts_late_fees_avoided_and_yield() -> None:
    terms = EarlyPaymentDiscount(percent=Decimal(2), days=10)
    planned = plan(
        [obligation("F-1", discount=terms), obligation("F-2", due=date(2026, 10, 31), late_fee_pct="1")], TREASURY
    )
    value = captured_value(planned, 2026, 10)
    assert value.discounts == Decimal("73.00")
    assert value.late_fees_avoided == Decimal("36.50")
    assert value.treasury_yield == Decimal("8.80")  # F-1 kept 8 days (USD 3,20) + F-2 kept 14 days (USD 5,60)
    assert value.total == Decimal("118.30")
    assert value.payments == 2


# Properties ----------------------------------------------------------------------------------------------------

obligations = st.lists(
    st.builds(
        lambda n, amount, due, critical: obligation(
            f"F-{n}", amount=str(amount), due=TODAY + timedelta(days=due), critical=critical
        ),
        st.integers(0, 10_000),
        st.decimals(min_value=Decimal(1), max_value=Decimal(40000), places=2),
        st.integers(-30, 60),
        st.booleans(),
    ),
    max_size=25,
    unique_by=lambda o: o.invoice_id,
)


@settings(max_examples=200, deadline=None)
@given(obligations, st.decimals(min_value=Decimal(0), max_value=Decimal(200000), places=2))
def test_the_planned_payments_never_take_the_balance_under_the_reserve(items: list[Obligation], cash: Decimal) -> None:
    treasury = Treasury(today=TODAY, cash=cash, reserve=Decimal(50000), apy=Decimal(4), base_currency="USD")
    planned = plan(items, treasury)
    assert {p.obligation.invoice_id for p in planned} == {o.invoice_id for o in items}
    for point in projected_balance(planned, treasury, horizon_days=90):
        assert point.balance >= min(cash, treasury.reserve)
    assert all(p.pay_on is None or p.pay_on >= TODAY for p in planned)
