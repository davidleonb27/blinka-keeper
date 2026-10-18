"""The API the browser e2e walks (apps/web `npm run e2e`): production wiring, without the model.

Everything the web depends on is real: the demo company and its cases, the decision engine, the independent auditor,
the simulator, the hash-chained ledger and the database (SQLite from CUSTODIO_DATABASE_URL). Only the lanes that
call Claude are swapped for the deterministic doubles of the API tests, so the walk needs no key, spends nothing
and gets the same answers every run. Run: `uvicorn tests.e2e_app:app` from apps/api.

With CUSTODIO_E2E_STRIPE=fake the panel pays through the real Stripe rail and reads transfers back through the real
lookup, both over the fake Stripe transport of the payment tests: the acta's «Pago en Stripe» and /pagos without a key.
"""

from __future__ import annotations

import os
import time
from dataclasses import replace

from sqlalchemy.orm import Session

from custodio.api.app import create_app
from custodio.config import get_settings
from custodio.payments import STRIPE_TEST, RailChoice, StripeAccountTable, StripeApiLookup, StripeTestRail
from custodio.payments.port import Clock, PaymentRail
from custodio.services.context import production_runtime

from .api import doubles
from .payments.stripe_fake import FakeStripe
from .reconciliation.doubles import FakeStatementReader


def fake_stripe_rail() -> RailChoice:
    client = FakeStripe(seconds=lambda: int(time.time())).client()

    def build(session: Session, clock: Clock) -> PaymentRail:
        return StripeTestRail(client, StripeAccountTable(session, clock), clock=clock)

    return RailChoice(name=STRIPE_TEST, build=build, lookup=StripeApiLookup(client))


runtime = production_runtime(get_settings())
model_free = replace(
    runtime.lanes,
    extract_document=doubles.extract_document,
    extract_text=doubles.extract_text,
    compile_policy=doubles.compile_policy,
    narrate=doubles.narrate,
    profile_company=doubles.profile_company,
    import_suppliers=doubles.import_suppliers,
    red_team=doubles.red_team,
    triage_attack=doubles.triage_attack,
    read_statement=FakeStatementReader(),
)
# Every browser of the walk calls from 127.0.0.1: the per-IP model limit would count all of them as one visitor and
# refuse whichever test lands in a busy minute. The per-workspace limit still holds.
limits = replace(runtime.limits, model_calls_per_minute_per_ip=1000)
rail = fake_stripe_rail() if os.environ.get("CUSTODIO_E2E_STRIPE") == "fake" else runtime.payment_rail
app = create_app(replace(runtime, lanes=model_free, limits=limits, payment_rail=rail))
