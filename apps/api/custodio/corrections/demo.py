"""The demo company's invoice a visitor can play supplier with: stopped for a cause the supplier fixes, small enough
that the corrected one is paid alone within the reserve, and from a supplier with no incident on record."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from custodio.contracts import InvoiceCase, InvoiceSource, InvoiceSpec, Policy
from custodio.dataset.reading import read_spec

BLURRED_AMOUNT = 0.6  # a phone photo: the total could not be read with confidence, so R1 escalates
SEEDS = (
    (
        "F-039",
        datetime(2026, 10, 15, 16, 0, tzinfo=UTC),
        InvoiceSpec(
            supplier_name="Valentina Ortiz",
            supplier_tax_id="1.032.448.902",
            tax_label="CC",
            invoice_number="VO-11",
            issue_date=date(2026, 10, 15),
            due_date=date(2026, 10, 30),
            amount=Decimal(1900),
            currency="USD",
            bank_name="Bancolombia",
            account_number="0612-9156",
            description="Pruebas de regresión, segunda quincena de octubre 2026",
            channel=InvoiceSource.WHATSAPP,
            note="Hola, te mando foto de la cuenta de cobro de la segunda quincena.",
        ),
    ),
)


def seed_cases(policy: Policy, customer: str) -> list[InvoiceCase]:
    """Only for a company that has the supplier registered: the demo, never a company of its own."""
    registered = {beneficiary.tax_id for beneficiary in policy.beneficiaries}
    return [
        InvoiceCase(
            id=case_id,
            received_at=received_at,
            extraction=read_spec(
                spec, document_id=f"demo-{case_id}", customer=customer, confidence={"amount": BLURRED_AMOUNT}
            ),
        )
        for case_id, received_at, spec in SEEDS
        if spec.supplier_tax_id in registered
    ]
