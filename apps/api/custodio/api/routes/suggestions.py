from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from custodio.api.deps import CurrentWorkspace, Services
from custodio.contracts import Policy
from custodio.services import suggestion_service
from custodio.services.suggestion_service import DEFAULT_MIN_APPROVALS, Suggestion

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

MAX_MIN_APPROVALS = 50


class AcceptBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approver: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    expected_policy_version: int = Field(ge=1)  # the version whose simulation the person saw


@router.get("", response_model=list[Suggestion])
def list_suggestions(
    ctx: Services,
    workspace: CurrentWorkspace,
    min_approvals: Annotated[int, Query(ge=1, le=MAX_MIN_APPROVALS)] = DEFAULT_MIN_APPROVALS,
) -> list[Suggestion]:
    """Agreement changes drawn from repeated approvals, each with its evidence and simulation. Nothing is applied."""
    return suggestion_service.suggestions(ctx, workspace, min_approvals)


@router.post("/{suggestion_id}/accept", response_model=Policy)
def accept_suggestion(suggestion_id: str, body: AcceptBody, ctx: Services, workspace: CurrentWorkspace) -> Policy:
    return suggestion_service.accept(
        ctx, workspace, suggestion_id, approver=body.approver, simulated_on=body.expected_policy_version
    )
