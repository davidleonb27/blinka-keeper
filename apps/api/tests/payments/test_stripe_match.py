"""Keeper's record against Stripe's transfers: one transfer per recorded payment, the same amount, nothing extra."""

from __future__ import annotations

from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from custodio.payments import StripeTransfer
from custodio.payments.stripe_match import RecordedPayment, match

WORKSPACE = "ws_a"
WHEN = datetime(2026, 10, 18, tzinfo=UTC)


def transfer(
    transfer_id: str, cents: int, *, workspace: str = WORKSPACE, invoice: str = "F01", reversed_cents: int = 0
) -> StripeTransfer:
    return StripeTransfer(
        id=transfer_id,
        amount_cents=cents,
        currency="usd",
        destination="acct_x",
        created=WHEN,
        livemode=False,
        reversed=False,
        amount_reversed_cents=reversed_cents,
        transfer_group=f"{workspace}:{invoice}",
        metadata={"workspace_id": workspace, "invoice_id": invoice},
        balance=None,
        fetched_at=WHEN,
        raw={},
    )


def paid(invoice_id: str, cents: int, transfer_id: str) -> RecordedPayment:
    return RecordedPayment(
        invoice_id=invoice_id, supplier_name="Andes Code SAS", amount_cents=cents, transfer_id=transfer_id
    )


def kinds(result: object) -> list[tuple[str | None, str]]:
    return [(line.invoice_id, line.kind) for line in result.lines]  # type: ignore[attr-defined]


def test_every_recorded_payment_with_its_transfer_of_the_same_amount_balances() -> None:
    result = match(
        WORKSPACE,
        [paid("F01", 120_050, "tr_1"), paid("F03", 900, "tr_2")],
        [transfer("tr_1", 120_050), transfer("tr_2", 900, invoice="F03")],
    )

    assert kinds(result) == [("F01", "matched"), ("F03", "matched")]
    assert (result.recorded_cents, result.stripe_cents) == (120_950, 120_950)
    assert result.balanced is True


def test_a_recorded_payment_without_its_transfer_is_missing_in_stripe() -> None:
    result = match(WORKSPACE, [paid("F01", 100, "tr_1"), paid("F02", 200, "tr_gone")], [transfer("tr_1", 100)])

    assert kinds(result) == [("F01", "matched"), ("F02", "missing_in_stripe")]
    assert result.balanced is False
    assert (result.recorded_cents, result.stripe_cents) == (300, 100)


def test_a_transfer_nobody_recorded_is_missing_in_the_registry() -> None:
    stray = transfer("tr_stray", 5_000, invoice="F99")

    result = match(WORKSPACE, [paid("F01", 100, "tr_1")], [transfer("tr_1", 100), stray])

    assert kinds(result) == [("F01", "matched"), ("F99", "missing_in_registry")]
    assert result.stripe_cents == 5_100
    assert result.balanced is False


def test_a_different_amount_or_a_reversal_is_a_difference() -> None:
    result = match(
        WORKSPACE,
        [paid("F01", 100, "tr_1"), paid("F02", 200, "tr_2")],
        [transfer("tr_1", 150), transfer("tr_2", 200, invoice="F02", reversed_cents=200)],
    )

    assert kinds(result) == [("F01", "amount_differs"), ("F02", "amount_differs")]
    assert [line.stripe_cents for line in result.lines] == [150, 0]


def test_two_records_pointing_at_one_transfer_use_it_once() -> None:
    result = match(WORKSPACE, [paid("F01", 100, "tr_1"), paid("F02", 100, "tr_1")], [transfer("tr_1", 100)])

    assert kinds(result) == [("F01", "matched"), ("F02", "missing_in_stripe")]


def test_another_workspace_s_transfers_never_enter_the_match() -> None:
    theirs = transfer("tr_theirs", 9_999, workspace="ws_b")

    result = match(WORKSPACE, [paid("F01", 100, "tr_1")], [transfer("tr_1", 100), theirs])

    assert kinds(result) == [("F01", "matched")]
    assert result.stripe_cents == 100
    assert result.balanced is True


@given(st.lists(st.integers(min_value=1, max_value=10_000_000), max_size=12), st.randoms())
def test_the_match_does_not_depend_on_the_order_stripe_answers_in(amounts: list[int], rng: object) -> None:
    recorded = [paid(f"F{i:02d}", cents, f"tr_{i}") for i, cents in enumerate(amounts)]
    transfers = [transfer(f"tr_{i}", cents, invoice=f"F{i:02d}") for i, cents in enumerate(amounts)]
    shuffled = list(transfers)
    rng.shuffle(shuffled)  # type: ignore[attr-defined]

    assert match(WORKSPACE, recorded, shuffled) == match(WORKSPACE, list(reversed(recorded)), transfers)
    assert match(WORKSPACE, recorded, transfers).balanced is True
