"""Which rail this deployment pays with. Stripe only in test mode: a live key is refused, never used.

Blinka has no public API yet, so its rail only builds the instruction it would send (see `custodio.payments.blinka`).
"""

from __future__ import annotations

import logging

import stripe
from sqlalchemy.orm import Session

from custodio.payments.accounts import StripeAccountTable
from custodio.payments.blinka import BlinkaRail
from custodio.payments.port import BLINKA_SIMULATED, SIMULATED, STRIPE_TEST, Clock, PaymentRail, RailChoice
from custodio.payments.simulated import SimulatedRail
from custodio.payments.stripe_lookup import CachedLookup, StripeApiLookup
from custodio.payments.stripe_rail import StripeTestRail

logger = logging.getLogger(__name__)

TEST_KEY_PREFIX = "sk_test_"
LIVE_KEY_PREFIXES = ("sk_live_", "rk_live_")
NETWORK_RETRIES = 2  # safe: every write carries an idempotency key


def simulated_choice() -> RailChoice:
    return RailChoice(name=SIMULATED, build=_simulated)


def choose_rail(requested: str, secret_key: str | None) -> RailChoice:
    """`requested` is CUSTODIO_PAYMENT_RAIL and `secret_key` is STRIPE_SECRET_KEY; neither is ever logged."""
    rail = requested.strip().lower()
    if rail == BLINKA_SIMULATED:
        return RailChoice(name=BLINKA_SIMULATED, build=_blinka)
    if rail != STRIPE_TEST:
        return simulated_choice()
    key = (secret_key or "").strip()
    if key.startswith(LIVE_KEY_PREFIXES):
        logger.warning("STRIPE_SECRET_KEY is a live key and Keeper only pays in test mode: using the simulated rail")
        return simulated_choice()
    if not key.startswith(TEST_KEY_PREFIX):
        logger.warning("CUSTODIO_PAYMENT_RAIL=stripe_test needs a sk_test_ STRIPE_SECRET_KEY: using the simulated rail")
        return simulated_choice()
    client = stripe.StripeClient(key, max_network_retries=NETWORK_RETRIES)

    def build(session: Session, clock: Clock) -> PaymentRail:
        return StripeTestRail(client, StripeAccountTable(session, clock), clock=clock)

    return RailChoice(name=STRIPE_TEST, build=build, lookup=CachedLookup(StripeApiLookup.with_key(key)))


def _simulated(_: Session, clock: Clock) -> PaymentRail:
    return SimulatedRail(clock)


def _blinka(_: Session, clock: Clock) -> PaymentRail:
    return BlinkaRail(clock)
