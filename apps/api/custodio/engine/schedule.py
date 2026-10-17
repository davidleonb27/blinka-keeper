"""When to pay what is already approved. Pure: the same obligations and treasury always give the same plan.

- A payment goes out on its due date, not before, so the cash earns its yield in the account for as long as it can.
- It goes out earlier only to earn an early-payment discount (e.g. 2/10 net 30), on the discount's last day, and only
  when the discount is worth more than the yield given up by not waiting for the due date.
- Overdue payments, and those without a due date, go out today.
- The reserve (R12) is never touched: when the cash minus the reserve does not reach for everything, payments are
  admitted by priority (the agreed late fee first, then critical suppliers, then the earliest due date) and the rest
  wait, with the reason.

Every amount is in the base currency. The yield rate is an assumption the deployment configures, never a promise.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum

from custodio.contracts import EarlyPaymentDiscount
from custodio.engine.formatting import CENT, HUNDRED, day_month, money, percent

DAYS_PER_YEAR = Decimal(365)


class Timing(StrEnum):
    DISCOUNT = "discount"  # early, to earn the discount
    ON_DUE = "on_due"
    OVERDUE = "overdue"
    NO_DUE_DATE = "no_due_date"
    SHORT_OF_CASH = "short_of_cash"  # waits: paying it would touch the reserve


@dataclass(frozen=True)
class Obligation:
    """A payment already approved (by the agent or a person) whose money is still in the account."""

    invoice_id: str
    beneficiary_id: str | None
    supplier_name: str
    amount: Decimal | None
    currency: str | None
    amount_base: Decimal
    approved_on: date  # it would have gone out that day without a scheduler: the yield counts from here
    issue_date: date | None
    due_date: date | None
    discount: EarlyPaymentDiscount | None
    late_fee_pct: Decimal | None  # per month overdue, as agreed
    critical: bool


@dataclass(frozen=True)
class Treasury:
    today: date
    cash: Decimal  # in the account now, before any of the obligations go out
    reserve: Decimal
    apy: Decimal  # annual yield of the cash in percent, e.g. 4.0: a configured assumption
    base_currency: str


@dataclass(frozen=True)
class PlannedPayment:
    obligation: Obligation
    pay_on: date | None  # None while the cash does not reach without touching the reserve
    timing: Timing
    reason: str  # Spanish, with the figures
    discount_base: Decimal
    late_fee_avoided_base: Decimal
    yield_base: Decimal


@dataclass(frozen=True)
class BalancePoint:
    day: date
    balance: Decimal


@dataclass(frozen=True)
class CapturedValue:
    discounts: Decimal
    late_fees_avoided: Decimal
    treasury_yield: Decimal
    payments: int

    @property
    def total(self) -> Decimal:
        return self.discounts + self.late_fees_avoided + self.treasury_yield


def plan(obligations: Iterable[Obligation], treasury: Treasury) -> list[PlannedPayment]:
    """Each obligation with its day, in payment order; the ones that wait for cash come last."""
    room = treasury.cash - treasury.reserve
    planned = []
    for obligation in sorted(obligations, key=_priority):
        if obligation.amount_base > room:
            planned.append(_waits(obligation, treasury, room))
            continue
        room -= obligation.amount_base
        planned.append(_timed(obligation, treasury))
    return sorted(planned, key=_payment_order)


def settled(obligation: Obligation, paid_on: date, treasury: Treasury) -> PlannedPayment:
    """A payment that already went out, valued by the day it did."""
    deadline = _discount_deadline(obligation)
    if deadline is not None and paid_on <= deadline:
        return _payment(obligation, paid_on, Timing.DISCOUNT, "", treasury)
    due = obligation.due_date
    timing = Timing.NO_DUE_DATE if due is None else Timing.OVERDUE if paid_on > due else Timing.ON_DUE
    return _payment(obligation, paid_on, timing, "", treasury)


def projected_balance(planned: Sequence[PlannedPayment], treasury: Treasury, horizon_days: int) -> list[BalancePoint]:
    points, balance = [], treasury.cash
    for offset in range(horizon_days + 1):
        day = treasury.today + timedelta(days=offset)
        balance -= sum((p.obligation.amount_base for p in planned if p.pay_on == day), Decimal(0))
        points.append(BalancePoint(day, balance))
    return points


def captured_value(payments: Iterable[PlannedPayment], year: int, month: int) -> CapturedValue:
    """What paying at the right time is worth in a month: discounts, late fees avoided and the cash's yield."""
    in_month = [p for p in payments if p.pay_on is not None and (p.pay_on.year, p.pay_on.month) == (year, month)]
    return CapturedValue(
        discounts=sum((p.discount_base for p in in_month), Decimal(0)),
        late_fees_avoided=sum((p.late_fee_avoided_base for p in in_month), Decimal(0)),
        treasury_yield=sum((p.yield_base for p in in_month), Decimal(0)),
        payments=len(in_month),
    )


# Timing --------------------------------------------------------------------------------------------------------


def _timed(obligation: Obligation, treasury: Treasury) -> PlannedPayment:
    today, due, base = treasury.today, obligation.due_date, treasury.base_currency
    deadline = _discount_deadline(obligation)
    if deadline is not None and deadline >= today and obligation.discount is not None:
        discount = _discount(obligation)
        waiting = _yield(obligation.amount_base, deadline, due, treasury.apy) if due else Decimal(0)
        if discount > waiting:
            reason = (
                f"Se adelanta al {day_month(deadline)}: el {percent(obligation.discount.percent / HUNDRED)} de "
                f"descuento por pronto pago ({money(discount, base)}) vale más que el rendimiento de esperar al "
                f"vencimiento ({money(waiting, base)})."
            )
            return _payment(obligation, deadline, Timing.DISCOUNT, reason, treasury)
    if due is None:
        reason = "La factura no trae fecha de vencimiento: se paga hoy."
        return _payment(obligation, today, Timing.NO_DUE_DATE, reason, treasury)
    if due < today:
        reason = f"Venció el {day_month(due)}: se paga hoy para no sumar más días de mora."
        return _payment(obligation, today, Timing.OVERDUE, reason, treasury)
    payment = _payment(obligation, due, Timing.ON_DUE, "", treasury)
    reason = (
        f"Se paga el {day_month(due)}, el día del vencimiento y no antes: el saldo rinde "
        f"{money(payment.yield_base, base)} más en la cuenta"
    )
    if payment.late_fee_avoided_base:
        reason += f" y se evita la mora pactada de {money(payment.late_fee_avoided_base, base)}"
    return replace(payment, reason=reason + ".")


def _waits(obligation: Obligation, treasury: Treasury, room: Decimal) -> PlannedPayment:
    base = treasury.base_currency
    reason = (
        f"Espera: pagar {money(obligation.amount_base, base)} dejaría el saldo proyectado bajo la reserva de "
        f"{money(treasury.reserve, base)}. Quedan {money(max(room, Decimal(0)), base)} y van primero los pagos con "
        "mora pactada y los proveedores críticos."
    )
    zero = Decimal(0)
    return PlannedPayment(obligation, None, Timing.SHORT_OF_CASH, reason, zero, zero, zero)


def _payment(obligation: Obligation, day: date, timing: Timing, reason: str, treasury: Treasury) -> PlannedPayment:
    due = obligation.due_date
    on_time = due is not None and day <= due and obligation.late_fee_pct is not None
    return PlannedPayment(
        obligation=obligation,
        pay_on=day,
        timing=timing,
        reason=reason,
        discount_base=_discount(obligation) if timing is Timing.DISCOUNT else Decimal(0),
        late_fee_avoided_base=_cents(obligation.amount_base * (obligation.late_fee_pct or 0) / HUNDRED)
        if on_time
        else Decimal(0),
        yield_base=_yield(obligation.amount_base, obligation.approved_on, day, treasury.apy),
    )


def _discount_deadline(obligation: Obligation) -> date | None:
    terms, issued = obligation.discount, obligation.issue_date
    if terms is None or issued is None:
        return None
    return issued + timedelta(days=terms.days)


def _discount(obligation: Obligation) -> Decimal:
    terms = obligation.discount
    return _cents(obligation.amount_base * terms.percent / HUNDRED) if terms else Decimal(0)


def _yield(amount: Decimal, start: date, end: date, apy: Decimal) -> Decimal:
    days = max(0, (end - start).days)
    return _cents(amount * apy / HUNDRED * days / DAYS_PER_YEAR)


def _priority(obligation: Obligation) -> tuple[Decimal, bool, date, str]:
    late_fee = obligation.amount_base * (obligation.late_fee_pct or 0)
    return (-late_fee, not obligation.critical, obligation.due_date or date.min, obligation.invoice_id)


def _payment_order(planned: PlannedPayment) -> tuple[bool, date, tuple[Decimal, bool, date, str]]:
    return (planned.pay_on is None, planned.pay_on or date.max, _priority(planned.obligation))


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_EVEN)
