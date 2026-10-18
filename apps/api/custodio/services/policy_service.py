"""Versioned policies: read, apply (always a new version in the ledger), compile from Spanish and simulate."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select

from custodio.contracts import (
    Beneficiary,
    CompanyState,
    LedgerEntry,
    LedgerKind,
    Policy,
    PolicyProposal,
    SimulationReport,
)
from custodio.db.models import PolicyRow, WorkspaceRow
from custodio.engine.text import normalize_code, normalize_name
from custodio.llm import LLMError
from custodio.services import ledger_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import PolicyChanged, PolicyInvalid, model_failure

AMOUNT_FIELDS = ("approval_threshold", "per_payment_limit", "period_budget", "reserve", "agreement_tolerance_pct")
WINDOW_FIELDS = ("duplicate_window_days", "split_window_days")


class PolicyVersion(BaseModel):
    version: int
    at: datetime
    author: str | None  # who made the change, when a person made it through an approval or a suggestion
    reason: str | None
    invoice_id: str | None  # the invoice whose approval updated the agreement
    suggestion_id: str | None  # the suggestion the person accepted
    changed_fields: list[str]
    hash: str


def current(ctx: ServiceContext, workspace_id: str) -> Policy:
    row = ctx.session.scalars(
        select(PolicyRow).where(PolicyRow.workspace_id == workspace_id).order_by(PolicyRow.version.desc()).limit(1)
    ).one()
    return Policy.model_validate(row.document)


def apply(ctx: ServiceContext, workspace_id: str, policy: Policy, context: dict[str, Any] | None = None) -> Policy:
    """`context` adds what else changed with this version (e.g. the company set up in onboarding) to the ledger."""
    _validate(policy)
    previous = current(ctx, workspace_id)
    return store(ctx, workspace_id, policy.model_copy(update={"version": previous.version + 1}), previous, context)


def add_beneficiaries(ctx: ServiceContext, workspace_id: str, added: list[Beneficiary]) -> Policy:
    """A new version with `added` appended and nothing else changed. A supplier that shares an id, a tax id or a name
    (or alias) with a registered one, or with another in `added`, is refused: a change of bank details arrives on an
    invoice and goes through R4, R13 and R15, never through here."""
    policy = current(ctx, workspace_id)
    taken: set[str] = set()
    for beneficiary in policy.beneficiaries:
        taken |= _identity_keys(beneficiary)
    for beneficiary in added:
        keys = _identity_keys(beneficiary)
        if not normalize_code(beneficiary.tax_id) or not normalize_name(beneficiary.name):
            raise PolicyInvalid(f"Faltan el nombre o la identificación tributaria de «{beneficiary.name}».")
        if keys & taken:
            raise PolicyInvalid(f"«{beneficiary.name}» ya está registrado; sus datos no se cambian desde aquí.")
        taken |= keys
    return apply(ctx, workspace_id, policy.model_copy(update={"beneficiaries": [*policy.beneficiaries, *added]}))


def _identity_keys(beneficiary: Beneficiary) -> set[str]:
    names = {f"name:{normalize_name(n)}" for n in (beneficiary.name, *beneficiary.aliases) if normalize_name(n)}
    tax_id = normalize_code(beneficiary.tax_id)
    return {f"id:{beneficiary.id}", *names, *([f"tax:{tax_id}"] if tax_id else [])}


def store(
    ctx: ServiceContext,
    workspace_id: str,
    policy: Policy,
    previous: Policy | None = None,
    context: dict[str, Any] | None = None,
) -> Policy:
    ctx.session.add(
        PolicyRow(
            workspace_id=workspace_id,
            version=policy.version,
            document=policy.model_dump(mode="json"),
            created_at=ctx.now(),
        )
    )
    payload = {"version": policy.version, "changed_fields": _changed_fields(previous, policy), **(context or {})}
    ledger_service.append(ctx, workspace_id, LedgerKind.POLICY_CHANGED, f"policy-v{policy.version}", payload)
    return policy


def compile_text(ctx: ServiceContext, workspace: WorkspaceRow, text: str, base: Policy | None = None) -> PolicyProposal:
    """The model proposes; the engine simulates the proposal against everything this workspace has received.

    With a `base` draft (a company still onboarding) there is no history of that policy to replay, so no simulation.
    """
    policy = base or current(ctx, workspace.id)
    try:
        proposal = ctx.lanes.compile_policy(text, policy)
    except LLMError as error:
        raise model_failure(error) from error
    if base is not None:
        return proposal
    return proposal.model_copy(update={"simulation": simulate(ctx, workspace, proposal.proposed)})


def simulate(ctx: ServiceContext, workspace: WorkspaceRow, proposed: Policy) -> SimulationReport:
    """Replays everything this workspace has received under the current policy and under `proposed`."""
    cases = [records.as_case(row) for row in records.invoices(ctx, workspace.id)]
    return ctx.lanes.simulate(cases, opening_state(ctx, workspace), current(ctx, workspace.id), proposed)


def apply_reviewed(
    ctx: ServiceContext, workspace_id: str, proposed: Policy, *, simulated_on: int, context: dict[str, Any]
) -> Policy:
    """Applies a change a person saw simulated on version `simulated_on`; refused if the policy moved since.

    The workspace lock makes a rival change wait, so two people confirming at once get a refusal, not a clash."""
    ledger_service.lock(ctx, workspace_id)
    if current(ctx, workspace_id).version != simulated_on:
        raise PolicyChanged()
    return apply(ctx, workspace_id, proposed, context)


def versions(ctx: ServiceContext, workspace_id: str) -> list[PolicyVersion]:
    """Every version, newest first, with who changed it, why and when, as the ledger holds it."""
    changes = ledger_service.entries(ctx, workspace_id, kinds=(LedgerKind.POLICY_CHANGED,))
    return [_version(entry) for entry in reversed(changes)]


def _version(entry: LedgerEntry) -> PolicyVersion:
    payload = entry.payload
    return PolicyVersion(
        version=int(payload["version"]),
        at=entry.at,
        author=_text(payload.get("author")),
        reason=_text(payload.get("reason")),
        invoice_id=_text(payload.get("invoice_id")),
        suggestion_id=_text(payload.get("suggestion_id")),
        changed_fields=[str(name) for name in payload.get("changed_fields", [])],
        hash=entry.hash,
    )


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def opening_state(ctx: ServiceContext, workspace: WorkspaceRow) -> CompanyState:
    """The company as it was seeded, so a simulation replays the whole history from the start."""
    state = records.company_state(ctx, workspace)
    return state.model_copy(
        update={"opening_balance": workspace.opening_balance, "history": records.seeded_history(workspace)}
    )


def _validate(policy: Policy) -> None:
    negative = [name for name in AMOUNT_FIELDS + WINDOW_FIELDS if getattr(policy, name) < 0]
    if negative:
        raise PolicyInvalid(f"Estos valores no pueden ser negativos: {', '.join(negative)}.")
    if not Decimal(0) <= policy.min_confidence <= Decimal(1):
        raise PolicyInvalid("La confianza mínima debe estar entre 0 y 1.")
    if policy.base_currency not in policy.allowed_currencies:
        raise PolicyInvalid("La moneda base debe estar entre las monedas permitidas.")


def _changed_fields(previous: Policy | None, policy: Policy) -> list[str]:
    if previous is None:
        return []
    before, after = previous.model_dump(exclude={"version"}), policy.model_dump(exclude={"version"})
    return sorted(name for name in after if after[name] != before[name])
