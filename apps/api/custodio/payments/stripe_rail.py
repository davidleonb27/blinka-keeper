"""Stripe in test mode: real API calls, test money.

Each beneficiary gets one Custom connected account, created with Stripe's test values so it is verified at once, and
each payment is a Transfer from the platform to that account. Stripe errors become a failed receipt with a Spanish
message; they never reach the API as exceptions.
"""

from __future__ import annotations

import hashlib
import logging
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

import stripe
from stripe.params import AccountCreateParams

from custodio.engine.text import normalize_name
from custodio.payments.port import STRIPE_TEST, Clock, PaymentOrder, PaymentReceipt

logger = logging.getLogger(__name__)

CURRENCY = "usd"
CENTS_PER_UNIT = Decimal(100)
TOP_UP_MARGIN_CENTS = 100_000  # 1.000 USD above what is missing, so the next payments do not top up again
TOP_UP_CARD = "pm_card_bypassPending"  # Stripe's test card whose funds are available at once
BALANCE_INSUFFICIENT = "balance_insufficient"
RETRY_SUFFIX = "tras-recarga"
TOP_UP_SUFFIX = "recarga"
DASHBOARD_TRANSFER_URL = "https://dashboard.stripe.com/test/connect/transfers/{}"
NAME_KEY_LENGTH = 200

# Stripe's test-mode values that make a Custom account verified on creation. Fixed, so a replayed request matches.
TEST_BIRTH_YEAR = 1901
TEST_SSN_LAST_4 = "0000"
TEST_ADDRESS_LINE = "address_full_match"
TEST_BANK_ACCOUNT = "btok_us_verified"
TEST_PHONE = "0000000000"
TOS_ACCEPTED_AT = 1_767_225_600  # 2026-01-01T00:00:00Z
TOS_IP = "8.8.8.8"
SOFTWARE_MCC = "5734"

NO_BENEFICIARY = "El pago no tiene un beneficiario registrado; no se envió nada a Stripe."
NO_AMOUNT = "El monto a transferir no es válido; no se envió nada a Stripe."
NO_TEST_FUNDS = "El saldo de prueba de Stripe no alcanzó ni después de recargarlo; no se transfirió dinero."
UNCONFIRMED = "No pudimos confirmar el pago con Stripe. Reintentar es seguro: Stripe no repite una transferencia."
KEY_REJECTED = "Stripe rechazó la clave de prueba configurada; no se transfirió dinero."
BUSY = "Stripe pidió esperar un momento; no se transfirió dinero. Reintenta el pago."
REJECTED = "Stripe rechazó el pago; no se transfirió dinero."
REJECTED_WITH_CODE = "Stripe rechazó el pago (código {}); no se transfirió dinero."


class AccountDirectory(Protocol):
    """Which Stripe test account pays each beneficiary, so accounts are created once and reused."""

    def find(self, beneficiary_id: str, name_key: str) -> str | None: ...

    def remember(self, beneficiary_id: str, name_key: str, account_id: str) -> str:
        """Stores the account unless one is already known, and returns the one that is kept."""
        ...


class StripeTestRail:
    name = STRIPE_TEST

    def __init__(self, client: stripe.StripeClient, accounts: AccountDirectory, *, clock: Clock) -> None:
        self._client = client
        self._accounts = accounts
        self._clock = clock

    def execute(self, order: PaymentOrder) -> PaymentReceipt:
        cents = to_cents(order.amount_base)
        if order.beneficiary_id is None:
            return self._failed(NO_BENEFICIARY)
        if cents <= 0:
            return self._failed(NO_AMOUNT)
        try:
            account = self._account(order.beneficiary_id, order.supplier_name)
            transfer = self._transfer_topping_up(order, account, cents)
        except stripe.StripeError as error:
            logger.warning("stripe refused a payment: %s %s", type(error).__name__, _safe_code(error))
            return self._failed(spanish_error(error))
        return PaymentReceipt(
            rail=STRIPE_TEST,
            status="executed",
            external_id=transfer.id,
            dashboard_url=DASHBOARD_TRANSFER_URL.format(transfer.id),
            executed_at=self._clock(),
        )

    def _account(self, beneficiary_id: str, supplier_name: str) -> str:
        name_key = name_key_of(supplier_name)
        known = self._accounts.find(beneficiary_id, name_key)
        if known is not None:
            return known
        account = self._client.v1.accounts.create(
            params=_account_params(beneficiary_id, supplier_name),
            options={"idempotency_key": _account_key(beneficiary_id, supplier_name)},
        )
        return self._accounts.remember(beneficiary_id, name_key, account.id)

    def _transfer_topping_up(self, order: PaymentOrder, account: str, cents: int) -> stripe.Transfer:
        try:
            return self._transfer(order, account, cents, order.idempotency_key)
        except stripe.InvalidRequestError as error:
            if error.code != BALANCE_INSUFFICIENT:
                raise
        self._top_up(cents, order.idempotency_key)
        # Stripe replays the stored answer of a used idempotency key, errors included: the retry needs its own key.
        return self._transfer(order, account, cents, f"{order.idempotency_key}:{RETRY_SUFFIX}")

    def _transfer(self, order: PaymentOrder, account: str, cents: int, key: str) -> stripe.Transfer:
        return self._client.v1.transfers.create(
            params={
                "amount": cents,
                "currency": CURRENCY,
                "destination": account,
                "description": f"Custodio · factura {order.invoice_id}",
                "metadata": {
                    "workspace_id": order.workspace_id,
                    "invoice_id": order.invoice_id,
                    "acta_url": order.acta_url,
                },
            },
            options={"idempotency_key": key},
        )

    def _top_up(self, transfer_cents: int, key: str) -> None:
        """Adds test money to the platform balance with Stripe's test card. Only ever runs with a test key."""
        balance = self._client.v1.balance.retrieve()
        available = sum(funds.amount for funds in balance.available if funds.currency == CURRENCY)
        self._client.v1.payment_intents.create(
            params={
                "amount": max(transfer_cents - available, 0) + TOP_UP_MARGIN_CENTS,
                "currency": CURRENCY,
                "payment_method": TOP_UP_CARD,
                "automatic_payment_methods": {"enabled": True, "allow_redirects": "never"},
                "confirm": True,
                "description": "Custodio · recarga del saldo de prueba",
            },
            options={"idempotency_key": f"{key}:{TOP_UP_SUFFIX}"},
        )

    def _failed(self, message: str) -> PaymentReceipt:
        return PaymentReceipt(rail=STRIPE_TEST, status="failed", executed_at=self._clock(), error=message)


def to_cents(amount: Decimal) -> int:
    return int((amount * CENTS_PER_UNIT).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def name_key_of(supplier_name: str) -> str:
    return normalize_name(supplier_name)[:NAME_KEY_LENGTH]


def spanish_error(error: stripe.StripeError) -> str:
    """Built from the error's type and code only: Stripe's own message can quote part of the key."""
    code = _safe_code(error)
    if isinstance(error, stripe.APIConnectionError):
        return UNCONFIRMED
    if isinstance(error, stripe.AuthenticationError | stripe.PermissionError):
        return KEY_REJECTED
    if isinstance(error, stripe.RateLimitError):
        return BUSY
    if code == BALANCE_INSUFFICIENT:
        return NO_TEST_FUNDS
    return REJECTED_WITH_CODE.format(code) if code else REJECTED


def _safe_code(error: stripe.StripeError) -> str | None:
    code = error.code
    return code if isinstance(code, str) and re.fullmatch(r"[a-z0-9_]{1,64}", code) else None


def _account_key(beneficiary_id: str, supplier_name: str) -> str:
    spelling = hashlib.sha256(supplier_name.encode()).hexdigest()[:16]
    return f"custodio-cuenta:{beneficiary_id}:{spelling}"


def _account_params(beneficiary_id: str, supplier_name: str) -> AccountCreateParams:
    return {
        "type": "custom",
        "country": "US",
        "business_type": "individual",
        "capabilities": {"transfers": {"requested": True}},
        "individual": {
            "first_name": "Proveedor",
            "last_name": "Prueba",
            "email": "proveedor.prueba@example.com",
            "phone": TEST_PHONE,
            "dob": {"day": 1, "month": 1, "year": TEST_BIRTH_YEAR},
            "ssn_last_4": TEST_SSN_LAST_4,
            "address": {
                "line1": TEST_ADDRESS_LINE,
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94111",
                "country": "US",
            },
        },
        "external_account": TEST_BANK_ACCOUNT,
        "tos_acceptance": {"date": TOS_ACCEPTED_AT, "ip": TOS_IP},
        "business_profile": {
            "name": supplier_name,
            "mcc": SOFTWARE_MCC,
            "product_description": "Proveedor de prueba pagado por Custodio",
        },
        "metadata": {"beneficiary_id": beneficiary_id},
    }
