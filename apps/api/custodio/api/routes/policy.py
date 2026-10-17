from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from custodio.api.deps import CurrentWorkspace, ModelCallLimit, Services
from custodio.contracts import Policy, PolicyProposal
from custodio.services import policy_service

router = APIRouter(prefix="/policy", tags=["policy"])

MAX_RULES_TEXT = 4000


class CompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=MAX_RULES_TEXT)
    base: Policy | None = None  # a draft to compile against (onboarding) instead of the workspace policy


@router.get("", response_model=Policy)
def read_policy(ctx: Services, workspace: CurrentWorkspace) -> Policy:
    return policy_service.current(ctx, workspace.id)


@router.put("", response_model=Policy)
def apply_policy(policy: Policy, ctx: Services, workspace: CurrentWorkspace) -> Policy:
    return policy_service.apply(ctx, workspace.id, policy)


@router.post("/compile", response_model=PolicyProposal, dependencies=[ModelCallLimit])
def compile_policy(body: CompileRequest, ctx: Services, workspace: CurrentWorkspace) -> PolicyProposal:
    return policy_service.compile_text(ctx, workspace, body.text, body.base)
