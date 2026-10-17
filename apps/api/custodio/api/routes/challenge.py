from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from custodio.api.deps import ClientIp, RuntimeDep, Services
from custodio.api.routes.invoices import media_type_of
from custodio.contracts import ChallengeAttempt, ChallengeStats
from custodio.services import challenge_service, rate_limits
from custodio.services.challenge_service import AttackInput, UploadedAttack
from custodio.services.errors import InvoiceInputMissing

router = APIRouter(prefix="/challenge", tags=["challenge"])

MAX_ATTACK_TEXT = 20_000


def limit_attempts(runtime: RuntimeDep, ip: ClientIp) -> None:
    rate_limits.check_challenge_attempt(runtime, ip=ip)


@router.post("/attempts", status_code=201, response_model=ChallengeAttempt, dependencies=[Depends(limit_attempts)])
def submit_attempt(
    ctx: Services,
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form(max_length=MAX_ATTACK_TEXT)] = None,
    alias: Annotated[str | None, Form(max_length=60)] = None,
    technique: Annotated[str | None, Form(max_length=120)] = None,
) -> ChallengeAttempt:
    return challenge_service.attempt(
        ctx, AttackInput(text=text, document=_document(file, text), alias=alias, technique=technique)
    )


@router.get("/stats", response_model=ChallengeStats)
def read_stats(ctx: Services) -> ChallengeStats:
    return challenge_service.stats(ctx)


def _document(file: UploadFile | None, text: str | None) -> UploadedAttack | None:
    if file is not None:
        filename = file.filename or "trampa"
        return UploadedAttack(
            data=file.file.read(), filename=filename, media_type=media_type_of(file.content_type, filename)
        )
    if not text or not text.strip():
        raise InvoiceInputMissing()
    return None
