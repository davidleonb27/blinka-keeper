"""One supplier's agreement changed and nothing else: the only kind of policy change approvals and suggestions make.

Global caps (R9–R12), the reserve and the hard rules live elsewhere in the policy, so a change built here cannot
reach them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from custodio.contracts import Agreement, AgreementKind, Beneficiary, Policy, PolicyChange
from custodio.services.errors import AgreementNotAvailable, PolicyInvalid

MAX_TOLERANCE_PCT = Decimal(100)


@dataclass(frozen=True)
class AgreementUpdate:
    amount: Decimal | None = None  # the newly agreed amount, in the agreement's currency
    tolerance_pct: Decimal | None = None  # this supplier's tolerance, overriding the policy's

    @property
    def empty(self) -> bool:
        return self.amount is None and self.tolerance_pct is None


def effective_tolerance(agreement: Agreement, policy: Policy) -> Decimal:
    return agreement.tolerance_pct if agreement.tolerance_pct is not None else policy.agreement_tolerance_pct


def updated(
    policy: Policy, beneficiary_id: str | None, update: AgreementUpdate, *, currency: str | None, quote: str
) -> tuple[Policy, list[PolicyChange]]:
    """The policy with that supplier's agreement updated, and the changes as the rules screen shows them.

    A supplier without an agreement gets a fixed one in `currency` (the invoice's) when the update sets an amount.
    """
    _validate(update)
    supplier = next((b for b in policy.beneficiaries if b.id == beneficiary_id), None)
    if supplier is None:
        raise AgreementNotAvailable()
    before = supplier.agreement or _new_agreement(update, currency)
    after = before.model_copy(update=_fields(update))
    changes = _changes(supplier, before if supplier.agreement else None, after, policy, quote)
    if not changes:
        raise PolicyInvalid("El acuerdo ya dice eso; no hay nada que cambiar.")
    beneficiaries = [
        b.model_copy(update={"agreement": after}) if b.id == supplier.id else b for b in policy.beneficiaries
    ]
    return policy.model_copy(update={"beneficiaries": beneficiaries}), changes


def _validate(update: AgreementUpdate) -> None:
    if update.empty:
        raise PolicyInvalid("Indica el nuevo monto acordado o la nueva tolerancia.")
    if update.amount is not None and update.amount <= 0:
        raise PolicyInvalid("El monto acordado debe ser mayor que cero.")
    if update.tolerance_pct is not None and not Decimal(0) <= update.tolerance_pct <= MAX_TOLERANCE_PCT:
        raise PolicyInvalid("La tolerancia debe estar entre 0 % y 100 %.")


def _new_agreement(update: AgreementUpdate, currency: str | None) -> Agreement:
    if update.amount is None or currency is None:
        raise PolicyInvalid("Este proveedor no tiene acuerdo: indica el monto acordado para crearlo.")
    return Agreement(kind=AgreementKind.FIXED, amount=update.amount, currency=currency)


def _fields(update: AgreementUpdate) -> dict[str, Decimal]:
    fields = {"amount": update.amount, "tolerance_pct": update.tolerance_pct}
    return {name: value for name, value in fields.items() if value is not None}


def _changes(
    supplier: Beneficiary, before: Agreement | None, after: Agreement, policy: Policy, quote: str
) -> list[PolicyChange]:
    path = f"beneficiaries[{supplier.id}].agreement"
    old_amount = before.amount if before else None
    old_tolerance = effective_tolerance(before, policy) if before else None
    pairs = [
        ("amount", f"Monto acordado con {supplier.name}", old_amount, after.amount),
        ("tolerance_pct", f"Tolerancia de {supplier.name} (%)", old_tolerance, effective_tolerance(after, policy)),
    ]
    return [
        PolicyChange(field=f"{path}.{name}", label=label, before=_shown(old), after=_shown(new), source_quote=quote)
        for name, label, old, new in pairs
        if old != new
    ]


def _shown(value: Decimal | None) -> str | None:
    return None if value is None else f"{value.normalize():f}"
