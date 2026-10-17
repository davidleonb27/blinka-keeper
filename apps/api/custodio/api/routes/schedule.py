from __future__ import annotations

from fastapi import APIRouter

from custodio.api.deps import CurrentWorkspace, Services
from custodio.services import schedule_service
from custodio.services.schedule_service import RunDue, ScheduleView

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("", response_model=ScheduleView)
def read_schedule(ctx: Services, workspace: CurrentWorkspace) -> ScheduleView:
    """The next 45 days of approved payments: when each goes out, through which rail and why then."""
    return schedule_service.view(ctx, workspace)


@router.post("/run-due", response_model=RunDue)
def run_due(ctx: Services, workspace: CurrentWorkspace) -> RunDue:
    """Pays what is due today or earlier through the configured rail. Running it twice pays nothing twice."""
    return schedule_service.run_due(ctx, workspace)
