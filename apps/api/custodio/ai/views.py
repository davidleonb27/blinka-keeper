"""What a model may see of a company's configuration: rules and names, never accounts or contacts."""

from __future__ import annotations

import json
from typing import Any

from custodio.contracts import Policy

_PRIVATE_BENEFICIARY_FIELDS = {"account_number", "approver_contact"}


def policy_view(policy: Policy) -> dict[str, Any]:
    view = policy.model_dump(mode="json", exclude={"beneficiaries", "approvers"})
    view["beneficiaries"] = [
        b.model_dump(mode="json", exclude=_PRIVATE_BENEFICIARY_FIELDS) for b in policy.beneficiaries
    ]
    view["approvers"] = [{"name": a.name, "role": a.role} for a in policy.approvers]
    return view


def as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True)
