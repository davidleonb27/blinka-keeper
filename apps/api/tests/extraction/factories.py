from datetime import date
from decimal import Decimal
from typing import Any

from custodio.contracts import InvoiceSpec


def make_spec(**overrides: Any) -> InvoiceSpec:
    fields: dict[str, Any] = {
        "supplier_name": "Nube Andina S.A.S.",
        "supplier_tax_id": "900.123.456-7",
        "invoice_number": "FE-2041",
        "issue_date": date(2026, 10, 5),
        "due_date": date(2026, 10, 20),
        "amount": Decimal("4200000"),
        "currency": "COP",
        "bank_name": "Bancolombia",
        "account_number": "123-456789-01",
        "description": "Servicio de nube y respaldo, octubre 2026",
    }
    return InvoiceSpec(**(fields | overrides))
