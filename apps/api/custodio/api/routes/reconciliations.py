from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from custodio.api.deps import ClientIp, CurrentWorkspace, RuntimeDep, Services
from custodio.api.routes.invoices import media_type_of
from custodio.reconciliation.models import MatchSettings
from custodio.services import rate_limits, reconciliation_service
from custodio.services.errors import StatementInputMissing
from custodio.services.reconciliation_service import ReconciliationItem, ReconciliationView, Upload

router = APIRouter(prefix="/reconciliations", tags=["reconciliations"])

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ResolveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    movement_id: Annotated[str, StringConstraints(min_length=1, max_length=16)]
    reviewer: PersonName
    note: Note


@router.post("", status_code=201, response_model=ReconciliationView)
def create_reconciliation(
    ctx: Services,
    runtime: RuntimeDep,
    workspace: CurrentWorkspace,
    ip: ClientIp,
    file: Annotated[UploadFile | None, File()] = None,
    demo: Annotated[bool, Form()] = False,
    fx_tolerance_pct: Annotated[Decimal | None, Form(ge=0, le=5)] = None,
) -> ReconciliationView:
    """Reconciles a bank statement (CSV, PDF or image) or the demo statement against what this workspace paid."""
    settings = MatchSettings() if fx_tolerance_pct is None else MatchSettings(fx_tolerance_pct=fx_tolerance_pct)
    if demo:
        return reconciliation_service.reconcile_demo(ctx, workspace, settings)
    if file is None:
        raise StatementInputMissing()
    filename = file.filename or "extracto"
    upload = Upload(data=file.file.read(), filename=filename, media_type=media_type_of(file.content_type, filename))
    if reconciliation_service.reads_with_model(upload):
        rate_limits.check_model_call(runtime, ip=ip, workspace_id=workspace.id)
    return reconciliation_service.reconcile_upload(ctx, workspace, upload, settings)


@router.get("", response_model=list[ReconciliationItem])
def list_reconciliations(ctx: Services, workspace: CurrentWorkspace) -> list[ReconciliationItem]:
    return reconciliation_service.history(ctx, workspace)


@router.get(
    "/demo-statement",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}, "application/pdf": {}}}},
)
def download_demo_statement(
    ctx: Services, workspace: CurrentWorkspace, format: Annotated[Literal["csv", "pdf"], Query()] = "csv"
) -> Response:
    """The demo statement, moved to the day this workspace paid its batch."""
    statement = reconciliation_service.demo_statement(ctx, workspace, format)
    return Response(
        content=statement.data,
        media_type=statement.media_type,
        headers={"Content-Disposition": f'attachment; filename="{statement.filename}"'},
    )


@router.get("/{reconciliation_id}", response_model=ReconciliationView)
def read_reconciliation(reconciliation_id: str, ctx: Services, workspace: CurrentWorkspace) -> ReconciliationView:
    return reconciliation_service.get(ctx, workspace, reconciliation_id)


@router.post("/{reconciliation_id}/resolve", response_model=ReconciliationView)
def resolve_movement(
    reconciliation_id: str, body: ResolveBody, ctx: Services, workspace: CurrentWorkspace
) -> ReconciliationView:
    """A person marks a movement that needed review as reviewed, with a note. It stays in the ledger."""
    return reconciliation_service.resolve(
        ctx, workspace, reconciliation_id, movement_id=body.movement_id, reviewer=body.reviewer, note=body.note
    )
