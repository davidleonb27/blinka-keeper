"""Who is this supplier? Matching by tax id or by normalized name and aliases."""

from __future__ import annotations

from dataclasses import dataclass

from custodio.contracts import Beneficiary, Policy
from custodio.engine.text import normalize_name, normalize_tax_id


@dataclass(frozen=True)
class BeneficiaryMatch:
    """`beneficiary` is the allowed-list entry the supplier is; `name_lookalike` is set when the name matches an
    entry but the identity does not (an impostor or a conflicting tax id)."""

    beneficiary: Beneficiary | None
    name_lookalike: Beneficiary | None = None


def match_beneficiary(policy: Policy, *, name: str | None, tax_id: str | None) -> BeneficiaryMatch:
    by_name = _find_by_name(policy, name) if name else None
    if not tax_id or not normalize_tax_id(tax_id):
        return BeneficiaryMatch(beneficiary=by_name)
    by_tax_id = _find_by_tax_id(policy, tax_id)
    if by_tax_id is None or (by_name is not None and by_name.id != by_tax_id.id):
        return BeneficiaryMatch(beneficiary=None, name_lookalike=by_name)
    return BeneficiaryMatch(beneficiary=by_tax_id)


def _find_by_tax_id(policy: Policy, tax_id: str) -> Beneficiary | None:
    wanted = normalize_tax_id(tax_id)
    return next((b for b in policy.beneficiaries if normalize_tax_id(b.tax_id) == wanted), None)


def _find_by_name(policy: Policy, name: str) -> Beneficiary | None:
    wanted = normalize_name(name)
    if not wanted:
        return None
    return next(
        (b for b in policy.beneficiaries if wanted in {normalize_name(n) for n in (b.name, *b.aliases)}),
        None,
    )
