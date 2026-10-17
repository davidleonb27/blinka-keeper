"""Payment rails: how a payment the engine already decided leaves the building. See docs/PAYMENTS.md."""

from custodio.payments.accounts import StripeAccountTable
from custodio.payments.choice import choose_rail, simulated_choice
from custodio.payments.port import (
    SIMULATED,
    STRIPE_TEST,
    Clock,
    PaymentOrder,
    PaymentRail,
    PaymentReceipt,
    RailChoice,
    RailName,
)
from custodio.payments.simulated import SimulatedRail
from custodio.payments.stripe_rail import StripeTestRail

__all__ = [
    "SIMULATED",
    "STRIPE_TEST",
    "Clock",
    "PaymentOrder",
    "PaymentRail",
    "PaymentReceipt",
    "RailChoice",
    "RailName",
    "SimulatedRail",
    "StripeAccountTable",
    "StripeTestRail",
    "choose_rail",
    "simulated_choice",
]
