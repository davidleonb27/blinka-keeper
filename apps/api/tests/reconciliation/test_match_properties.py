"""Hypothesis properties of the matcher on random statements: no movement is used twice, nothing reconciled exceeds
its movement, and the outcome does not depend on the order of the inputs."""

import random
from collections import Counter
from datetime import date
from decimal import Decimal

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from custodio.reconciliation.match import reconcile
from custodio.reconciliation.models import (
    NEEDS_REVIEW,
    MatchSettings,
    MovementStatus,
    PaidInvoice,
    ReconciliationOutcome,
    StatementMovement,
)

from .builders import day

PROPERTY = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
NAMES = ("Andes Code SAS", "Pulso Software Inc.", "Pixel Norte S.A. de C.V.", "Café Origen SAS", "Diego Salazar")
CENTS = st.integers(min_value=1, max_value=500_000).map(lambda cents: Decimal(cents) / 100)
DAYS = st.integers(min_value=10, max_value=24)


@st.composite
def payments(draw: st.DrawFn) -> list[PaidInvoice]:
    count = draw(st.integers(min_value=0, max_value=6))
    made = []
    for index in range(count):
        foreign = draw(st.booleans())
        base = draw(CENTS)
        made.append(
            PaidInvoice(
                invoice_id=f"F-{index:03d}",
                invoice_number=draw(st.sampled_from([None, f"INV-{index}", f"INV-{index}0"])),
                supplier_name=(name := draw(st.sampled_from(NAMES))),
                names=[name],
                amount=base * 4000 if foreign else base,
                currency="COP" if foreign else "USD",
                amount_base=base,
                base_currency="USD",
                paid_on=day(draw(DAYS)),
                external_id=draw(st.sampled_from([None, f"tr_{index}abc"])),
                acta_url=f"https://custodio.test/acta/F-{index:03d}",
            )
        )
    return made


@st.composite
def statement(draw: st.DrawFn, made: list[PaidInvoice]) -> list[StatementMovement]:
    rows: list[tuple[date, Decimal, str]] = []
    for payment in made:
        shape = draw(st.sampled_from(["exact", "cents", "split", "missing", "twice"]))
        label = f"PAGO {payment.invoice_number or ''} {payment.supplier_name}"
        on = day(draw(DAYS))
        if shape == "exact":
            rows.append((on, -payment.amount_base, label))
        elif shape == "cents":
            rows.append((on, -payment.amount_base + Decimal(draw(st.integers(-30, 30))) / 100, label))
        elif shape == "split":
            first = (payment.amount_base / 3).quantize(Decimal("0.01"))
            rows += [(on, -first, label), (on, -(payment.amount_base - first), label)]
        elif shape == "twice":
            rows += [(on, -payment.amount_base, label), (on, -payment.amount_base, label)]
    for _ in range(draw(st.integers(min_value=0, max_value=4))):
        rows.append((day(draw(DAYS)), draw(CENTS) * draw(st.sampled_from([-1, 1])), draw(st.sampled_from(NAMES))))
    for _ in range(draw(st.integers(min_value=0, max_value=2))):
        rows.append((day(draw(DAYS)), -draw(CENTS), "COMISION TRANSFERENCIA"))
    return [
        StatementMovement(
            id=f"m{index:03d}",
            row=index,
            booked_on=on,
            description=label,
            amount=amount,
            currency="USD",
            quote=f"{on};{label};{amount}",
            read=draw(st.booleans()) or draw(st.booleans()),
        )
        for index, (on, amount, label) in enumerate(rows, start=1)
    ]


@st.composite
def scenario(draw: st.DrawFn) -> tuple[list[StatementMovement], list[PaidInvoice]]:
    made = draw(payments())
    return draw(statement(made)), made


def run(movements: list[StatementMovement], made: list[PaidInvoice]) -> ReconciliationOutcome:
    return reconcile(movements, made, [], MatchSettings())


@PROPERTY
@given(scenario())
def test_no_movement_is_used_twice(case: tuple[list[StatementMovement], list[PaidInvoice]]) -> None:
    movements, made = case
    outcome = run(movements, made)

    used = Counter(movement_id for payment in outcome.payments for movement_id in payment.movement_ids)
    assert all(count == 1 for count in used.values())
    matched = {item.movement_id: item.invoice_id for item in outcome.movements if item.invoice_id is not None}
    assert set(matched) == set(used)
    for payment in outcome.payments:
        assert all(matched[movement_id] == payment.invoice_id for movement_id in payment.movement_ids)


@PROPERTY
@given(scenario())
def test_what_is_reconciled_never_exceeds_the_movement(
    case: tuple[list[StatementMovement], list[PaidInvoice]],
) -> None:
    movements, made = case
    outcome = run(movements, made)

    by_id = {movement.id: movement for movement in movements}
    for item in outcome.movements:
        movement = by_id[item.movement_id]
        assert 0 <= item.allocated <= abs(movement.amount or 0)
        if item.invoice_id is None:
            assert item.allocated == 0
        else:
            assert movement.read and movement.amount is not None and movement.amount < 0


@PROPERTY
@given(scenario())
def test_alerts_are_only_outflows_or_unread_rows(case: tuple[list[StatementMovement], list[PaidInvoice]]) -> None:
    movements, made = case
    outcome = run(movements, made)

    by_id = {movement.id: movement for movement in movements}
    for item in outcome.movements:
        movement = by_id[item.movement_id]
        if item.status in NEEDS_REVIEW and item.status is not MovementStatus.UNREAD:
            assert movement.amount is not None and movement.amount < 0


def projection(outcome: ReconciliationOutcome, movements: list[StatementMovement]) -> Counter[tuple[object, ...]]:
    """The outcome by movement content, since ids follow the input order."""
    by_id = {movement.id: movement for movement in movements}

    def content(movement_id: str | None) -> tuple[object, ...] | None:
        if movement_id is None:
            return None
        movement = by_id[movement_id]
        return (movement.booked_on, movement.amount, movement.description, movement.read)

    return Counter(
        (
            content(item.movement_id),
            item.status,
            item.level,
            item.invoice_id,
            item.allocated,
            item.difference,
            content(item.duplicate_of),
        )
        for item in outcome.movements
    )


@PROPERTY
@given(scenario(), st.randoms(use_true_random=False))
def test_the_outcome_does_not_depend_on_the_input_order(
    case: tuple[list[StatementMovement], list[PaidInvoice]], rng: random.Random
) -> None:
    movements, made = case
    shuffled_movements, shuffled_payments = list(movements), list(made)
    rng.shuffle(shuffled_movements)
    rng.shuffle(shuffled_payments)

    original = run(movements, made)
    shuffled = run(shuffled_movements, shuffled_payments)

    assert projection(original, movements) == projection(shuffled, movements)
    assert [p.model_dump(exclude={"movement_ids"}) for p in original.payments] == [
        p.model_dump(exclude={"movement_ids"}) for p in shuffled.payments
    ]
