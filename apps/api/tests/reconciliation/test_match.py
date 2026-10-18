"""Pairing statement movements with what Blinka Keeper paid: deterministic, in a fixed order of levels, with reasons."""

from decimal import Decimal

from custodio.contracts import DecisionStatus
from custodio.reconciliation.match import reconcile
from custodio.reconciliation.models import (
    MatchLevel,
    MatchSettings,
    MovementResult,
    MovementStatus,
    PaidInvoice,
    PaymentStatus,
    ReconciliationOutcome,
    StatementMovement,
    UnpaidInvoice,
)

from .builders import movement, paid, unpaid


def run(
    movements: list[StatementMovement],
    payments: list[PaidInvoice],
    unpaid_invoices: list[UnpaidInvoice] | None = None,
    settings: MatchSettings | None = None,
) -> ReconciliationOutcome:
    return reconcile(movements, payments, unpaid_invoices or [], settings or MatchSettings())


def result(outcome: ReconciliationOutcome, movement_id: str) -> MovementResult:
    return next(item for item in outcome.movements if item.movement_id == movement_id)


def test_a_reference_to_the_invoice_number_with_the_exact_amount_is_an_exact_match() -> None:
    outcome = run(
        [movement("m001", "-840.00", "PAGO PS-88412 PULSO SOFTWARE")], [paid("F-005", "PS-88412", "Pulso", "840")]
    )

    matched = result(outcome, "m001")
    assert matched.status is MovementStatus.RECONCILED
    assert matched.level is MatchLevel.EXACT
    assert matched.invoice_id == "F-005"
    assert matched.allocated == Decimal("840.00")
    assert "PS-88412" in matched.reason
    assert outcome.payments[0].status is PaymentStatus.CONFIRMED
    assert outcome.payments[0].movement_ids == ["m001"]


def test_the_stripe_transfer_id_is_a_reference() -> None:
    outcome = run(
        [movement("m001", "-290.00", "WIRE OUT", reference="tr_1QabcXYZ")],
        [paid("F-006", None, "Trazo Firmas Inc.", "290", external_id="tr_1QabcXYZ")],
    )

    matched = result(outcome, "m001")
    assert (matched.level, matched.invoice_id) == (MatchLevel.EXACT, "F-006")
    assert "tr_1QabcXYZ" in matched.reason


def test_the_acta_link_is_a_reference() -> None:
    outcome = run(
        [movement("m001", "-290.00", "PAGO https://custodio.test/acta/F-006")],
        [paid("F-006", "TZ-50017", "Trazo Firmas Inc.", "290")],
    )

    assert result(outcome, "m001").level is MatchLevel.EXACT


def test_an_invoice_number_inside_a_longer_one_is_not_a_reference() -> None:
    outcome = run(
        [movement("m001", "-2150.00", "PAGO AC-2026-10-S")], [paid("F-004", "AC-2026-10", "Andes Code SAS", "2150")]
    )

    assert result(outcome, "m001").status is MovementStatus.UNMATCHED_OUTFLOW


def test_without_a_reference_the_exact_amount_date_and_beneficiary_match() -> None:
    outcome = run(
        [movement("m001", "-1600.00", "TRANSFERENCIA DIEGO SALAZAR", on=18)],
        [paid("F-015", "DS-10", "Diego Salazar", "1600", on=16)],
    )

    matched = result(outcome, "m001")
    assert matched.status is MovementStatus.RECONCILED
    assert matched.level is MatchLevel.AMOUNT_DATE
    assert "2 días" in matched.reason


def test_the_beneficiary_is_recognized_without_punctuation_or_company_suffix() -> None:
    outcome = run(
        [movement("m001", "-3152.17", "TRANSF PIXEL NORTE SA DE CV")],
        [paid("F-007", "PN-1021", "Pixel Norte S.A. de C.V.", "58000", currency="MXN", amount_base="3152.173913")],
    )

    assert result(outcome, "m001").level is MatchLevel.AMOUNT_DATE


def test_a_movement_outside_the_date_window_does_not_match_by_amount() -> None:
    outcome = run(
        [movement("m001", "-1600.00", "TRANSFERENCIA DIEGO SALAZAR", on=20)],
        [paid("F-015", "DS-10", "Diego Salazar", "1600", on=16)],
    )

    assert result(outcome, "m001").status is MovementStatus.UNMATCHED_OUTFLOW
    assert outcome.payments[0].status is PaymentStatus.PENDING


def test_the_same_amount_and_date_without_the_beneficiary_does_not_match() -> None:
    outcome = run([movement("m001", "-1600.00", "TRANSFERENCIA")], [paid("F-015", "DS-10", "Diego Salazar", "1600")])

    assert result(outcome, "m001").status is MovementStatus.UNMATCHED_OUTFLOW


def test_a_payment_split_in_two_movements_that_add_up_exactly() -> None:
    outcome = run(
        [
            movement("m001", "-3000.00", "PAGO AC-2026-10 ANDES CODE 1/2"),
            movement("m002", "-1800.00", "PAGO AC-2026-10 ANDES CODE 2/2", on=17),
        ],
        [paid("F-004", "AC-2026-10", "Andes Code SAS", "4800")],
    )

    assert {result(outcome, m).level for m in ("m001", "m002")} == {MatchLevel.SPLIT}
    assert [result(outcome, m).allocated for m in ("m001", "m002")] == [Decimal("3000.00"), Decimal("1800.00")]
    assert outcome.payments[0].movement_ids == ["m001", "m002"]
    assert "2 movimientos" in result(outcome, "m001").reason


def test_split_pieces_that_do_not_add_up_are_not_a_split() -> None:
    outcome = run(
        [movement("m001", "-3000.00", "PAGO AC-2026-10"), movement("m002", "-1700.00", "PAGO AC-2026-10")],
        [paid("F-004", "AC-2026-10", "Andes Code SAS", "4800")],
    )

    assert {result(outcome, m).status for m in ("m001", "m002")} == {MovementStatus.UNMATCHED_OUTFLOW}


def test_a_foreign_currency_payment_within_the_fx_tolerance_matches_with_its_difference() -> None:
    outcome = run(
        [movement("m001", "-634.02", "PAGO KT-0921 KORA TRADUCCIONES")],
        [paid("F-001", "KT-0921", "Kora Traducciones SAS", "2600000", currency="COP", amount_base="634.146341")],
    )

    matched = result(outcome, "m001")
    assert matched.status is MovementStatus.RECONCILED_WITH_DIFFERENCE
    assert matched.level is MatchLevel.TOLERANCE
    assert matched.difference == Decimal("-0.13")
    assert matched.allocated == Decimal("634.02")
    assert "0,5 %" in matched.reason
    assert outcome.payments[0].difference == Decimal("-0.13")


def test_a_bank_amount_above_the_payment_allocates_only_the_payment() -> None:
    outcome = run(
        [movement("m001", "-2244.12", "PAGO MFR-031")],
        [paid("F-012", "MFR-031", "María Fernanda Ríos", "9200000", currency="COP", amount_base="2243.902439")],
    )

    matched = result(outcome, "m001")
    assert (matched.difference, matched.allocated) == (Decimal("0.22"), Decimal("2243.90"))


def test_the_fx_tolerance_never_applies_to_a_payment_in_the_account_currency() -> None:
    outcome = run([movement("m001", "-1399.90", "PAGO CH-1003")], [paid("F-014", "CH-1003", "Cumulus", "1400")])

    assert result(outcome, "m001").status is MovementStatus.UNMATCHED_OUTFLOW


def test_a_difference_beyond_the_tolerance_is_an_alert_that_names_the_payment() -> None:
    outcome = run(
        [movement("m001", "-600.00", "PAGO KT-0921")],
        [paid("F-001", "KT-0921", "Kora Traducciones SAS", "2600000", currency="COP", amount_base="634.146341")],
    )

    alert = result(outcome, "m001")
    assert alert.status is MovementStatus.UNMATCHED_OUTFLOW
    assert "F-001" in alert.reason


def test_the_tolerance_is_explicit_and_configurable() -> None:
    movements = [movement("m001", "-630.00", "PAGO KT-0921")]
    payments = [paid("F-001", "KT-0921", "Kora", "2600000", currency="COP", amount_base="634.146341")]

    strict = run(movements, payments)
    loose = run(movements, payments, settings=MatchSettings(fx_tolerance_pct=Decimal("1")))

    assert result(strict, "m001").status is MovementStatus.UNMATCHED_OUTFLOW
    assert result(loose, "m001").status is MovementStatus.RECONCILED_WITH_DIFFERENCE


def test_bank_charges_are_recognized_as_fees() -> None:
    outcome = run(
        [
            movement("m001", "-18.00", "COMISIÓN ENVÍO SWIFT"),
            movement("m002", "-12.00", "CUOTA DE MANEJO OCTUBRE"),
            movement("m003", "-3.50", "Wire transfer fee"),
        ],
        [],
    )

    assert {item.status for item in outcome.movements} == {MovementStatus.BANK_FEE}


def test_the_bank_listing_a_matched_movement_twice_is_a_duplicate() -> None:
    twin = "PAGO CH-2026-1003 CUMULUS HOSTING"
    outcome = run(
        [movement("m001", "-1400.00", twin, on=17), movement("m002", "-1400.00", twin, on=17)],
        [paid("F-014", "CH-2026-1003", "Cumulus Hosting LLC", "1400")],
    )

    assert result(outcome, "m001").status is MovementStatus.RECONCILED
    duplicate = result(outcome, "m002")
    assert duplicate.status is MovementStatus.DUPLICATE
    assert duplicate.duplicate_of == "m001"
    assert duplicate.allocated == 0


def test_two_identical_unexplained_outflows_are_one_alert_and_one_duplicate() -> None:
    outcome = run([movement("m001", "-99.00", "RETIRO"), movement("m002", "-99.00", "RETIRO")], [])

    assert [item.status for item in outcome.movements] == [MovementStatus.UNMATCHED_OUTFLOW, MovementStatus.DUPLICATE]


def test_money_coming_in_is_outside_accounts_payable() -> None:
    outcome = run([movement("m001", "18500.00", "ABONO CLIENTE NORTHWIND")], [])

    assert result(outcome, "m001").status is MovementStatus.INFLOW


def test_an_unread_movement_is_never_matched_even_if_it_names_a_payment() -> None:
    outcome = run([movement("m001", None, "PAGO PS-88412", read=False)], [paid("F-005", "PS-88412", "Pulso", "840")])

    assert result(outcome, "m001").status is MovementStatus.UNREAD
    assert outcome.payments[0].status is PaymentStatus.PENDING


def test_an_outflow_for_an_invoice_custodio_did_not_pay_is_a_red_alert_that_says_so() -> None:
    outcome = run(
        [movement("m001", "-2900.00", "TRANSFERENCIA ORBIT GROWTH PARTNERS OGP-17")],
        [],
        [unpaid("F-018", "OGP-17", "Orbit Growth Partners LLC", "2900")],
    )

    alert = result(outcome, "m001")
    assert alert.status is MovementStatus.UNMATCHED_OUTFLOW
    assert "F-018" in alert.reason
    assert "esperaba aprobación" in alert.reason


def test_a_payment_missing_from_the_statement_is_pending() -> None:
    outcome = run([], [paid("F-036", "CO-1016", "Café Origen SAS", "450000", currency="COP", amount_base="109.756")])

    (payment,) = outcome.payments
    assert payment.status is PaymentStatus.PENDING
    assert payment.expected == Decimal("109.76")
    assert "no aparece" in payment.reason


def test_a_misspelled_invoice_number_matches_by_amount_and_says_so() -> None:
    outcome = run(
        [movement("m001", "-3152.17", "PAGO PN-1201 PIXEL NORTE")],
        [paid("F-007", "PN-1021", "Pixel Norte S.A. de C.V.", "58000", currency="MXN", amount_base="3152.173913")],
    )

    matched = result(outcome, "m001")
    assert matched.level is MatchLevel.AMOUNT_DATE
    assert "PN-1201" in matched.reason
    assert "PN-1021" in matched.reason


def test_a_reference_wins_over_an_earlier_payment_with_the_same_amount() -> None:
    outcome = run(
        [movement("m001", "-1300.00", "PAGO CH-2026-1013 CUMULUS HOSTING")],
        [
            paid("F-014", "CH-2026-1003", "Cumulus Hosting LLC", "1300"),
            paid("F-031", "CH-2026-1013", "Cumulus Hosting LLC", "1300"),
        ],
    )

    assert result(outcome, "m001").invoice_id == "F-031"


def test_an_account_in_the_invoice_currency_compares_the_invoiced_amount() -> None:
    outcome = run(
        [movement("m001", "-2600000.00", "PAGO KT-0921", currency="COP")],
        [paid("F-001", "KT-0921", "Kora", "2600000", currency="COP", amount_base="634.146341")],
    )

    assert result(outcome, "m001").level is MatchLevel.EXACT


def test_payments_and_movements_keep_their_order_in_the_outcome() -> None:
    outcome = run(
        [movement("m002", "-1.00", "X"), movement("m001", "-2.00", "Y")],
        [paid("F-2", None, "B", "5"), paid("F-1", None, "A", "5")],
    )

    assert [item.movement_id for item in outcome.movements] == ["m002", "m001"]
    assert [item.invoice_id for item in outcome.payments] == ["F-1", "F-2"]


def test_unpaid_statuses_are_named_in_spanish() -> None:
    outcome = run(
        [movement("m001", "-400.00", "PAGO LW-2026-114")],
        [],
        [unpaid("F-033", "LW-2026-114", "Letterwerk GmbH", "400", DecisionStatus.HOLD)],
    )

    assert "retenida" in result(outcome, "m001").reason
