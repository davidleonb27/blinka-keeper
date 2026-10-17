from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from custodio.api.deps import CurrentWorkspace, Services
from custodio.services import workspace_service
from custodio.services.workspace_service import WorkspaceMode, WorkspaceSummary

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: WorkspaceMode = WorkspaceMode.DEMO


class WorkspaceCreated(BaseModel):
    workspace_id: str
    api_key: str  # shown once; only its SHA-256 is stored


@router.post("", status_code=201, response_model=WorkspaceCreated)
def create_workspace(body: CreateWorkspace, ctx: Services) -> WorkspaceCreated:
    created = workspace_service.create(ctx, body.mode)
    return WorkspaceCreated(workspace_id=created.workspace_id, api_key=created.api_key)


@router.get("/current", response_model=WorkspaceSummary)
def current_workspace(ctx: Services, workspace: CurrentWorkspace) -> WorkspaceSummary:
    return workspace_service.summary(ctx, workspace)
