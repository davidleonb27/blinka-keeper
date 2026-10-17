"""A month of invoices for the demo's «Simular 30 días»: seeded, so every run plays exactly the same month.

Three suppliers of the demo company bill through it:

- Cumulus Hosting LLC (b10), usage-based hosting, about twice a week. The demo batch leaves it supervised, so a person
  approves its first invoices; once it earns its cap the agent pays it alone. On the 23rd an invoice with the same
  look asks to pay a different account (R4): back to supervised.
- Talento Andino Nómina SAS (b21), payroll every two weeks, above the policy's threshold: a person approves it.
- Ruta Legal Abogados SAS (b9), weekly fees under the threshold: the agent pays them alone.

Amounts vary around each agreement with distinct steps, so no two invoices look like the same charge (R5).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from custodio.contracts import Beneficiary, CompanyState, InvoiceCase, InvoiceSource, InvoiceSpec, Policy
from custodio.dataset.reading import read_spec

SEED = 1330
DAYS = 30
NET_DAYS = 10  # every simulated invoice is due ten days after it is issued
FIRST_ARRIVAL = time(13, 30)
STEP_PCT = Decimal("0.01")  # amounts differ by whole percent steps: always more than R5's ±0,5 %
FRAUD_BANK = ("Banco Pichincha", "7741-0093")


@dataclass(frozen=True)
class Billing:
    beneficiary_id: str
    prefix: str
    days: tuple[int, ...]  # 1-based days of the month
    typical: Decimal
    spread_steps: int  # amounts move up to this many steps around `typical`
    description: str
    fraud_day: int | None = None


BILLINGS = (
    Billing("b10", "CUM", (2, 5, 9, 12, 16, 19, 23, 26, 30), Decimal(260), 6, "Nube por consumo", fraud_day=23),
    Billing("b21", "TAN", (13, 27), Decimal(26_000_000), 2, "Nómina quincenal tercerizada"),
    Billing("b9", "RLA", (4, 11, 18, 25), Decimal(12_500_000), 4, "Honorarios por caso"),
)


@dataclass(frozen=True)
class MonthInvoice:
    day: date
    case: InvoiceCase
    fraud: bool  # True only for the changed-account invoice: a person never approves it


def simulated_month(state: CompanyState, policy: Policy, start: date, seed: int = SEED) -> list[MonthInvoice]:
    """Every invoice of the month that starts on `start`, in arrival order."""
    rng = random.Random(seed)  # noqa: S311  # seeded on purpose: the demo replays the very same month
    known = {beneficiary.id: beneficiary for beneficiary in policy.beneficiaries}
    month = [
        invoice
        for billing in BILLINGS
        if billing.beneficiary_id in known
        for invoice in _bill(billing, known[billing.beneficiary_id], state, start, rng)
    ]
    return sorted(month, key=lambda invoice: (invoice.case.received_at, invoice.case.id))


def _bill(
    billing: Billing, supplier: Beneficiary, state: CompanyState, start: date, rng: random.Random
) -> list[MonthInvoice]:
    steps = rng.sample(range(-billing.spread_steps, billing.spread_steps + 1), len(billing.days))
    invoices = []
    for position, (day_of_month, step) in enumerate(zip(billing.days, steps, strict=True)):
        day = start + timedelta(days=day_of_month - 1)
        fraud = day_of_month == billing.fraud_day
        amount = _rounded(billing.typical * (1 + STEP_PCT * step), supplier.currency)
        bank, account = FRAUD_BANK if fraud else (supplier.bank_name, supplier.account_number)
        spec = InvoiceSpec(
            supplier_name=supplier.name,
            supplier_tax_id=supplier.tax_id,
            invoice_number=f"{billing.prefix}-{day:%Y%m%d}",
            issue_date=day,
            due_date=day + timedelta(days=NET_DAYS),
            amount=amount,
            currency=supplier.currency,
            bank_name=bank,
            account_number=account,
            description=billing.description,
            channel=InvoiceSource.EMAIL if position % 2 else InvoiceSource.PDF,
        )
        case_id = f"SIM-{day:%m%d}-{billing.prefix}"
        extraction = read_spec(spec, document_id=f"sim-{case_id}", customer=state.company_name, confidence={})
        received = datetime.combine(day, FIRST_ARRIVAL, tzinfo=UTC) + timedelta(minutes=rng.randrange(0, 240))
        invoices.append(MonthInvoice(day, InvoiceCase(id=case_id, received_at=received, extraction=extraction), fraud))
    return invoices


def _rounded(amount: Decimal, currency: str) -> Decimal:
    places = Decimal(1) if currency in ("COP", "CLP") else Decimal("0.01")
    return amount.quantize(places)
