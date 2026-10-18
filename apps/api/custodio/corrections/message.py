"""The message to the supplier: a fixed template filled with the assessment, the registered names and the link.

Nothing the invoice says is copied into it except a reference that looks like an invoice number, so a document cannot
make Custodio write to the supplier what the document wants.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from custodio.corrections.models import Issue
from custodio.engine.formatting import long_date

SAFE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_/.#]{0,29}")
ACCOUNT_WARNING = (
    "Custodio sólo paga a la cuenta registrada. Si la factura corregida trae otra cuenta, no se paga: los cambios de "
    "cuenta se verifican por otro canal con su contacto registrado."
)


def safe_reference(invoice_number: str | None) -> str | None:
    """The invoice number when it looks like one (letters, digits and separators, up to 30); otherwise nothing."""
    candidate = (invoice_number or "").strip()
    return candidate if SAFE_REFERENCE.fullmatch(candidate) else None


def compose_message(
    *, company: str, supplier: str, reference: str | None, issues: Sequence[Issue], link: str, expires_at: datetime
) -> str:
    invoice = f"la factura {reference}" if reference else "su factura"
    reasons = [f"{number}. {issue.problem} Se espera: {issue.expected}." for number, issue in enumerate(issues, 1)]
    return "\n".join(
        [
            f"Hola, {supplier}:",
            "",
            f"Le escribimos de parte de {company}. Recibimos {invoice} y todavía no podemos pagarla:",
            *reasons,
            "",
            f"Puede enviar la factura corregida o confirmar el dato aquí: {link}",
            f"El enlace sirve sólo para esta factura y vence el {long_date(expires_at.date())}.",
            ACCOUNT_WARNING,
            "",
            "Gracias.",
        ]
    )
