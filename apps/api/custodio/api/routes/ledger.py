from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from custodio.api.deps import CurrentWorkspace, Services
from custodio.contracts import LedgerEntry, LedgerVerification
from custodio.services import ledger_service
from custodio.services.ledger_service import TamperDemo

router = APIRouter(prefix="/ledger", tags=["ledger"])


class TamperRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int | None = Field(default=None, ge=1)


@router.get("", response_model=list[LedgerEntry])
def read_ledger(ctx: Services, workspace: CurrentWorkspace) -> list[LedgerEntry]:
    return ledger_service.entries(ctx, workspace.id)


@router.get("/verify", response_model=LedgerVerification)
def verify_ledger(ctx: Services, workspace: CurrentWorkspace) -> LedgerVerification:
    return ledger_service.verify(ctx, workspace.id)


@router.post("/tamper-demo", response_model=TamperDemo)
def tamper_demo(body: TamperRequest, ctx: Services, workspace: CurrentWorkspace) -> TamperDemo:
    return ledger_service.tamper_demo(ctx, workspace.id, body.seq)
