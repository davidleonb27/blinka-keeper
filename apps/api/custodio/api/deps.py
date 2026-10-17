"""Request-scoped dependencies: the unit of work, the caller's workspace, the caller's IP and the rate limits."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request

from custodio.db.models import WorkspaceRow
from custodio.services import rate_limits, workspace_service
from custodio.services.context import Runtime, ServiceContext
from custodio.services.errors import InvalidApiKey, WorkspaceHeaderMissing

BEARER = "bearer "


def get_runtime(request: Request) -> Runtime:
    runtime: Runtime = request.app.state.runtime
    runtime.database.ensure_migrated()
    return runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]


def get_services(runtime: RuntimeDep) -> Iterator[ServiceContext]:
    with runtime.database.session() as session:
        yield runtime.context(session)


Services = Annotated[ServiceContext, Depends(get_services)]


def current_workspace(
    ctx: Services, x_custodio_workspace: Annotated[str | None, Header(include_in_schema=False)] = None
) -> WorkspaceRow:
    if not x_custodio_workspace:
        raise WorkspaceHeaderMissing()
    return workspace_service.get(ctx, x_custodio_workspace.strip())


CurrentWorkspace = Annotated[WorkspaceRow, Depends(current_workspace)]


def api_key_workspace(ctx: Services, authorization: Annotated[str | None, Header()] = None) -> WorkspaceRow:
    return workspace_service.by_api_key(ctx, bearer_token(authorization))


ApiKeyWorkspace = Annotated[WorkspaceRow, Depends(api_key_workspace)]


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith(BEARER):
        raise InvalidApiKey()
    return authorization[len(BEARER) :].strip()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    return first or (request.client.host if request.client else "unknown")


ClientIp = Annotated[str, Depends(client_ip)]


def limit_model_calls(runtime: RuntimeDep, workspace: CurrentWorkspace, ip: ClientIp) -> None:
    rate_limits.check_model_call(runtime, ip=ip, workspace_id=workspace.id)


def limit_model_calls_by_key(runtime: RuntimeDep, workspace: ApiKeyWorkspace, ip: ClientIp) -> None:
    rate_limits.check_model_call(runtime, ip=ip, workspace_id=workspace.id)


ModelCallLimit = Depends(limit_model_calls)
ModelCallLimitByKey = Depends(limit_model_calls_by_key)
