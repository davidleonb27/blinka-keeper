"""What Stripe says about the payments Custodio sent, asked live, and the file that hands approved payments to Blinka.

Three views, each scoped to the caller's workspace:

- `proof`: the acta's «Pago en Stripe». The transfer is read back from Stripe and each field is checked against the
  acta (amount, currency, beneficiary, invoice). A transfer whose metadata names another workspace is never shown.
- `overview`: /pagos. The workspace's payments and the match of Custodio's record against Stripe's transfers.
- `pain001`: the approved payments as an ISO 20022 pain.001.001.09 file for Blinka.

Stripe failing is an answer here, not an error: the views say «No se pudo consultar Stripe ahora» and keep showing
what Custodio recorded.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

from custodio.contracts import Decision, DecisionStatus, PaymentExecution, Policy
from custodio.db.models import WorkspaceRow
from custodio.payments import STRIPE_TEST, RailName, StripeAccountTable, StripeTransfer, StripeUnavailableError
from custodio.payments.pain001 import CreditTransfer, Debtor, PaymentFile, render
from custodio.payments.stripe_match import MatchLine, RailMatch, RecordedPayment, match, settled_cents
from custodio.payments.stripe_rail import CENTS_PER_UNIT, CURRENCY, DASHBOARD_TRANSFER_URL, name_key_of, to_cents
from custodio.services import policy_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import NothingToExport

ProofStatus = Literal["verified", "mismatch", "missing", "unavailable", "not_applicable"]
CheckField = Literal["amount", "currency", "beneficiary", "invoice", "livemode", "reversal"]
TransferState = Literal["paid", "partially_reversed", "reversed"]
MatchStatus = Literal["balanced", "differences", "unavailable", "not_applicable"]

UNAVAILABLE = (
    "No se pudo consultar Stripe ahora. El pago sigue registrado en el acta; vuelve a intentar en unos segundos."
)
NO_LOOKUP = "Este despliegue no tiene una clave de prueba de Stripe para consultar el pago."
NOT_STRIPE = "Este pago no salió por Stripe, así que no hay transferencia que consultar."
MISSING = "Stripe no tiene ninguna transferencia con este id. El registro de Custodio y Stripe no coinciden."
FOREIGN = "La transferencia existe, pero Stripe la asocia a otro espacio de trabajo: no se muestra."
RAIL_NOT_STRIPE = "El riel activo no es Stripe: los pagos de este espacio no generan transferencias que cuadrar."
INCOMPLETE = "Stripe tiene más transferencias de las que se revisaron; el cuadre puede estar incompleto."
DEBTOR_ACCOUNT_PREFIX = "BLINKA-"  # the company's account at Blinka; a placeholder until Blinka assigns one
MESSAGE_PREFIX = "CUSTODIO"
MESSAGE_HASH_LENGTH = 8


class ProofCheck(BaseModel):
    field: CheckField
    expected: str
    actual: str | None
    ok: bool


class BalanceView(BaseModel):
    id: str
    amount: Decimal
    fee: Decimal
    net: Decimal
    status: str
    available_on: datetime | None


class StripeTransferView(BaseModel):
    id: str
    amount: Decimal
    currency: str
    destination: str | None
    created: datetime
    livemode: bool
    state: TransferState
    amount_reversed: Decimal
    balance_transaction: BalanceView | None


class StripeProof(BaseModel):
    """The acta's «Pago en Stripe»: Stripe's own answer about the transfer and how it compares with the acta."""

    invoice_id: str
    status: ProofStatus
    message: str | None
    checked_at: datetime
    transfer: StripeTransferView | None
    checks: list[ProofCheck]
    dashboard_url: str | None
    raw: dict[str, Any] | None  # Stripe's JSON as it answered, only for this workspace's own transfer


class PaymentRow(BaseModel):
    invoice_id: str
    supplier_name: str | None
    status: DecisionStatus
    amount: Decimal | None
    currency: str | None
    amount_base: Decimal | None
    execution: PaymentExecution | None


class MatchLineView(BaseModel):
    kind: Literal["matched", "amount_differs", "missing_in_stripe", "missing_in_registry"]
    invoice_id: str | None
    supplier_name: str | None
    recorded_amount: Decimal | None
    stripe_amount: Decimal | None
    transfer_id: str
    dashboard_url: str


class RailMatchView(BaseModel):
    """«Registro de Custodio ↔ Stripe»: amounts in USD, the currency the rail sends."""

    status: MatchStatus
    message: str | None
    checked_at: datetime
    complete: bool
    lines: list[MatchLineView]
    recorded_total: Decimal
    stripe_total: Decimal
    difference: Decimal


class PaymentsOverview(BaseModel):
    rail: RailName
    base_currency: str
    payments: list[PaymentRow]
    stripe: RailMatchView
    exportable: int  # approved payments that go into the file for Blinka


def proof(ctx: ServiceContext, workspace: WorkspaceRow, invoice_id: str) -> StripeProof:
    decision = records.decision(ctx, workspace.id, invoice_id)
    execution = decision.execution
    if execution is None or execution.rail != STRIPE_TEST or not execution.external_id:
        return _answer(ctx, invoice_id, "not_applicable", NOT_STRIPE)
    lookup = ctx.runtime.payment_rail.lookup
    if lookup is None:
        return _answer(ctx, invoice_id, "unavailable", NO_LOOKUP)
    try:
        transfer = lookup.transfer(execution.external_id)
    except StripeUnavailableError:
        return _answer(ctx, invoice_id, "unavailable", UNAVAILABLE)
    if transfer is None:
        return _answer(ctx, invoice_id, "missing", MISSING)
    if transfer.workspace_id != workspace.id:
        return _answer(ctx, invoice_id, "mismatch", FOREIGN)
    checks = _checks(ctx, decision, policy_service.current(ctx, workspace.id), transfer)
    return StripeProof(
        invoice_id=invoice_id,
        status="verified" if all(check.ok for check in checks) else "mismatch",
        message=None,
        checked_at=transfer.fetched_at,
        transfer=_transfer_view(transfer),
        checks=checks,
        dashboard_url=DASHBOARD_TRANSFER_URL.format(transfer.id),
        raw=transfer.raw,
    )


def overview(ctx: ServiceContext, workspace: WorkspaceRow) -> PaymentsOverview:
    policy = policy_service.current(ctx, workspace.id)
    paid = _paid(ctx, workspace.id)
    return PaymentsOverview(
        rail=ctx.runtime.payment_rail.name,
        base_currency=policy.base_currency,
        payments=[_payment_row(decision) for decision in paid],
        stripe=_rail_match(ctx, workspace, paid),
        exportable=len(_exportable(ctx, workspace.id, policy, None)),
    )


def pain001(ctx: ServiceContext, workspace: WorkspaceRow, decided_on: date | None) -> tuple[str, bytes]:
    """The file name and the XML. `decided_on` narrows the batch to the payments decided that day (UTC)."""
    policy = policy_service.current(ctx, workspace.id)
    transfers = _exportable(ctx, workspace.id, policy, decided_on)
    if not transfers:
        raise NothingToExport()
    now = ctx.now()
    message_id = _message_id(workspace.id, now, transfers)
    payment_file = PaymentFile(
        message_id=message_id,
        created_at=now,
        execution_date=now.date(),
        debtor=Debtor(name=workspace.company_name, account_id=f"{DEBTOR_ACCOUNT_PREFIX}{workspace.id}"),
        transfers=transfers,
    )
    return f"{message_id}.xml", render(payment_file)


def _answer(ctx: ServiceContext, invoice_id: str, status: ProofStatus, message: str) -> StripeProof:
    return StripeProof(
        invoice_id=invoice_id,
        status=status,
        message=message,
        checked_at=ctx.now(),
        transfer=None,
        checks=[],
        dashboard_url=None,
        raw=None,
    )


def _checks(ctx: ServiceContext, decision: Decision, policy: Policy, transfer: StripeTransfer) -> list[ProofCheck]:
    expected_cents = to_cents(decision.amount_base or Decimal(0))
    account = _expected_account(ctx, decision, policy)
    return [
        _check("amount", _units(expected_cents), _units(settled_cents(transfer))),
        _check("currency", CURRENCY, transfer.currency),
        ProofCheck(
            field="beneficiary",
            expected=account or "sin cuenta registrada",
            actual=transfer.destination,
            ok=account is not None and account == transfer.destination,
        ),
        _check("invoice", decision.invoice_id, transfer.invoice_id),
        _check("livemode", "false", str(transfer.livemode).lower()),
        _check("reversal", "0.00", _units(transfer.amount_reversed_cents)),
    ]


def _check(field: CheckField, expected: str, actual: str | None) -> ProofCheck:
    return ProofCheck(field=field, expected=expected, actual=actual, ok=expected == actual)


def _expected_account(ctx: ServiceContext, decision: Decision, policy: Policy) -> str | None:
    """The test account the rail pays this beneficiary through, keyed like the rail keys it: by the registered name."""
    registered = next((b for b in policy.beneficiaries if b.id == decision.beneficiary_id), None)
    if registered is None or decision.beneficiary_id is None:
        return None
    return StripeAccountTable(ctx.session, ctx.now).find(decision.beneficiary_id, name_key_of(registered.name))


def _transfer_view(transfer: StripeTransfer) -> StripeTransferView:
    balance = transfer.balance
    return StripeTransferView(
        id=transfer.id,
        amount=_decimal(transfer.amount_cents),
        currency=transfer.currency,
        destination=transfer.destination,
        created=transfer.created,
        livemode=transfer.livemode,
        state=_state(transfer),
        amount_reversed=_decimal(transfer.amount_reversed_cents),
        balance_transaction=None
        if balance is None
        else BalanceView(
            id=balance.id,
            amount=_decimal(balance.amount_cents),
            fee=_decimal(balance.fee_cents),
            net=_decimal(balance.net_cents),
            status=balance.status,
            available_on=balance.available_on,
        ),
    )


def _state(transfer: StripeTransfer) -> TransferState:
    if transfer.reversed or settled_cents(transfer) <= 0:
        return "reversed"
    return "partially_reversed" if transfer.amount_reversed_cents else "paid"


def _paid(ctx: ServiceContext, workspace_id: str) -> list[Decision]:
    return [decision for decision, _ in records.decisions(ctx, workspace_id) if decision.status in records.PAID]


def _payment_row(decision: Decision) -> PaymentRow:
    return PaymentRow(
        invoice_id=decision.invoice_id,
        supplier_name=decision.supplier_name,
        status=decision.status,
        amount=decision.amount,
        currency=decision.currency,
        amount_base=decision.amount_base,
        execution=decision.execution,
    )


def _rail_match(ctx: ServiceContext, workspace: WorkspaceRow, paid: Sequence[Decision]) -> RailMatchView:
    recorded = [_recorded(decision) for decision in paid if _sent_by_stripe(decision.execution)]
    lookup = ctx.runtime.payment_rail.lookup
    if lookup is None:
        return _empty_match(ctx, recorded, "not_applicable", RAIL_NOT_STRIPE)
    try:
        listing = lookup.transfers_since(workspace.created_at)
    except StripeUnavailableError:
        return _empty_match(ctx, recorded, "unavailable", UNAVAILABLE)
    result = match(workspace.id, recorded, listing.transfers)
    return RailMatchView(
        status="balanced" if result.balanced and listing.complete else "differences",
        message=None if listing.complete else INCOMPLETE,
        checked_at=listing.fetched_at,
        complete=listing.complete,
        lines=[_line_view(line) for line in result.lines],
        **_totals(result),
    )


def _empty_match(
    ctx: ServiceContext, recorded: Sequence[RecordedPayment], status: MatchStatus, message: str
) -> RailMatchView:
    total = _decimal(sum(payment.amount_cents for payment in recorded))
    return RailMatchView(
        status=status,
        message=message,
        checked_at=ctx.now(),
        complete=False,
        lines=[],
        recorded_total=total,
        stripe_total=Decimal(0),
        difference=Decimal(0),
    )


def _totals(result: RailMatch) -> dict[str, Decimal]:
    return {
        "recorded_total": _decimal(result.recorded_cents),
        "stripe_total": _decimal(result.stripe_cents),
        "difference": _decimal(result.stripe_cents - result.recorded_cents),
    }


def _sent_by_stripe(execution: PaymentExecution | None) -> bool:
    return (
        execution is not None
        and execution.rail == STRIPE_TEST
        and execution.status == "executed"
        and execution.external_id is not None
    )


def _recorded(decision: Decision) -> RecordedPayment:
    assert decision.execution is not None and decision.execution.external_id is not None
    return RecordedPayment(
        invoice_id=decision.invoice_id,
        supplier_name=decision.supplier_name,
        amount_cents=to_cents(decision.amount_base or Decimal(0)),
        transfer_id=decision.execution.external_id,
    )


def _line_view(line: MatchLine) -> MatchLineView:
    return MatchLineView(
        kind=line.kind,
        invoice_id=line.invoice_id,
        supplier_name=line.supplier_name,
        recorded_amount=None if line.recorded_cents is None else _decimal(line.recorded_cents),
        stripe_amount=None if line.stripe_cents is None else _decimal(line.stripe_cents),
        transfer_id=line.transfer_id,
        dashboard_url=DASHBOARD_TRANSFER_URL.format(line.transfer_id),
    )


def _exportable(
    ctx: ServiceContext, workspace_id: str, policy: Policy, decided_on: date | None
) -> list[CreditTransfer]:
    """Approved payments the auditor let through, with the registered beneficiary's bank details."""
    beneficiaries = {b.id: b for b in policy.beneficiaries}
    transfers: list[CreditTransfer] = []
    for row, _ in records.decided_rows(ctx, workspace_id):
        decision = Decision.model_validate(row.document)
        beneficiary = beneficiaries.get(decision.beneficiary_id or "")
        if decision.status not in records.PAID or row.audit_blocked or beneficiary is None:
            continue
        if decided_on is not None and row.decided_at.date() != decided_on:
            continue
        transfers.append(
            CreditTransfer(
                end_to_end_id=decision.invoice_id,
                amount=decision.amount if decision.amount is not None else decision.amount_base or Decimal(0),
                currency=decision.currency or policy.base_currency,
                creditor_name=beneficiary.name,
                creditor_tax_id=beneficiary.tax_id,
                creditor_country=beneficiary.country,
                creditor_bank=beneficiary.bank_name,
                creditor_account=beneficiary.account_number,
                remittance=records.acta_url(ctx.runtime.public_base_url, decision.invoice_id),
            )
        )
    return transfers


def _message_id(workspace_id: str, now: datetime, transfers: Sequence[CreditTransfer]) -> str:
    """Same batch, same day: same id, so Blinka can refuse a file it already took."""
    batch = ",".join(sorted(t.end_to_end_id for t in transfers))
    digest = hashlib.sha256(f"{workspace_id}|{batch}".encode()).hexdigest()[:MESSAGE_HASH_LENGTH]
    return f"{MESSAGE_PREFIX}-{now:%Y%m%d}-{digest}"


def _units(cents: int) -> str:
    return f"{_decimal(cents):.2f}"


def _decimal(cents: int) -> Decimal:
    return (Decimal(cents) / CENTS_PER_UNIT).quantize(Decimal("0.01"))
