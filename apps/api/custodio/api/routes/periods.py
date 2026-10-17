from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, StringConstraints

from custodio.api.deps import CurrentWorkspace, Services
from custodio.services import reconciliation_service
from custodio.services.reconciliation_service import PeriodCloseView

router = APIRouter(prefix="/periods", tags=["periods"])

Period = Annotated[str, PathParam(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="yyyy-mm")]


class CloseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closed_by: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


@router.post("/{period}/close", response_model=PeriodCloseView)
def close_period(period: Period, body: CloseBody, ctx: Services, workspace: CurrentWorkspace) -> PeriodCloseView:
    """Closes the month once no outflow without an invoice is left unreviewed. Written to the ledger."""
    return reconciliation_service.close_period(ctx, workspace, period, closed_by=body.closed_by)


@router.get("/{period}/evidence.zip", response_class=Response, responses={200: {"content": {"application/zip": {}}}})
def download_evidence(period: Period, ctx: Services, workspace: CurrentWorkspace) -> Response:
    """The accountant's pack: summary PDF, reconciliation CSV, actas and the ledger with its verification."""
    return Response(
        content=reconciliation_service.evidence(ctx, workspace, period),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{reconciliation_service.evidence_filename(period)}"'},
    )
