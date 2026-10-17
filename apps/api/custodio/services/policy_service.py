"""Versioned policies: read, apply (always a new version in the ledger), compile from Spanish and simulate."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from custodio.contracts import CompanyState, LedgerKind, Policy, PolicyProposal
from custodio.db.models import PolicyRow, WorkspaceRow
from custodio.llm import LLMError
from custodio.services import ledger_service, records
from custodio.services.context import ServiceContext
from custodio.services.errors import ModelUnavailable, PolicyInvalid

AMOUNT_FIELDS = ("approval_threshold", "per_payment_limit", "period_budget", "reserve", "agreement_tolerance_pct")
WINDOW_FIELDS = ("duplicate_window_days", "split_window_days")


def current(ctx: ServiceContext, workspace_id: str) -> Policy:
    row = ctx.session.scalars(
        select(PolicyRow).where(PolicyRow.workspace_id == workspace_id).order_by(PolicyRow.version.desc()).limit(1)
    ).one()
    return Policy.model_validate(row.document)


def apply(ctx: ServiceContext, workspace_id: str, policy: Policy) -> Policy:
    _validate(policy)
    previous = current(ctx, workspace_id)
    return store(ctx, workspace_id, policy.model_copy(update={"version": previous.version + 1}), previous)


def store(ctx: ServiceContext, workspace_id: str, policy: Policy, previous: Policy | None = None) -> Policy:
    ctx.session.add(
        PolicyRow(
            workspace_id=workspace_id,
            version=policy.version,
            document=policy.model_dump(mode="json"),
            created_at=ctx.now(),
        )
    )
    payload = {"version": policy.version, "changed_fields": _changed_fields(previous, policy)}
    ledger_service.append(ctx, workspace_id, LedgerKind.POLICY_CHANGED, f"policy-v{policy.version}", payload)
    return policy


def compile_text(ctx: ServiceContext, workspace: WorkspaceRow, text: str) -> PolicyProposal:
    """The model proposes; the engine simulates the proposal against everything this workspace has received."""
    policy = current(ctx, workspace.id)
    try:
        proposal = ctx.lanes.compile_policy(text, policy)
    except LLMError as error:
        raise ModelUnavailable() from error
    cases = [records.as_case(row) for row in records.invoices(ctx, workspace.id)]
    simulation = ctx.lanes.simulate(cases, opening_state(ctx, workspace), policy, proposal.proposed)
    return proposal.model_copy(update={"simulation": simulation})


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
