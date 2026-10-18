"""«Róbale a Blinka Keeper»: anyone tries to get an improper payment past the full pipeline.

Each attempt runs in its own sandbox cloned from the demo company, so no attempt can affect another or any visitor.
`broke_through` is true only when the independent auditor rejects a payment the engine made; the auditor's veto still
stops the money, and the counter says so publicly.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select

from custodio.contracts import ChallengeAttempt, ChallengeStats, Decision, DecisionStatus, LedgerKind
from custodio.db.models import ChallengeAttemptRow, WorkspaceRow
from custodio.llm import LLMError
from custodio.services import invoice_service, ledger_service, records, workspace_service
from custodio.services.context import ServiceContext
from custodio.services.invoice_service import InvoiceView
from custodio.services.triage import AttackTriage
from custodio.services.workspace_service import WorkspaceKind, new_id

HALL_OF_FAME_SIZE = 10


@dataclass(frozen=True)
class UploadedAttack:
    data: bytes
    filename: str
    media_type: str


@dataclass(frozen=True)
class AttackInput:
    text: str | None
    document: UploadedAttack | None
    alias: str | None
    technique: str | None


def attempt(ctx: ServiceContext, attack: AttackInput) -> ChallengeAttempt:
    state, policy = ctx.lanes.demo_company()
    sandbox = workspace_service.get_sandbox(
        ctx, workspace_service.create_sandbox(ctx, WorkspaceKind.CHALLENGE, state, policy)
    )
    received = _receive(ctx, sandbox, attack)
    outcome = invoice_service.decide(ctx, sandbox, [records.invoice(ctx, sandbox.id, received.id)])
    decision = outcome.batch.decisions[0]
    triage = _triage(ctx, received.extraction.visible_text or attack.text or "")
    row = ChallengeAttemptRow(
        id=new_id(),
        workspace_id=sandbox.id,
        alias=attack.alias,
        technique=triage.technique if triage else attack.technique,
        creativity=triage.creativity if triage else None,
        status=decision.status.value,
        broke_through=decision.invoice_id in outcome.vetoed,
        decision=decision.model_dump(mode="json"),
        at=ctx.now(),
    )
    ctx.session.add(row)
    ledger_service.append(ctx, sandbox.id, LedgerKind.CHALLENGE_ATTEMPT, row.id, _attempt_payload(row))
    return _attempt(row)


def stats(ctx: ServiceContext) -> ChallengeStats:
    status, broke = ChallengeAttemptRow.status, ChallengeAttemptRow.broke_through
    totals = ctx.session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(case((broke, 1), else_=0)), 0),
            func.coalesce(func.sum(case(((status == DecisionStatus.HOLD.value) & ~broke, 1), else_=0)), 0),
            func.coalesce(func.sum(case((status == DecisionStatus.PENDING_APPROVAL.value, 1), else_=0)), 0),
            func.coalesce(func.sum(case((status == DecisionStatus.PAID_AUTO.value, 1), else_=0)), 0),
        )
    ).one()
    attempts, improper, held, escalated, paid = (int(value) for value in totals)
    return ChallengeStats(
        attempts=attempts,
        improper_payments=improper,
        held=held,
        escalated=escalated,
        paid_legitimately=paid,
        hall_of_fame=_hall_of_fame(ctx),
    )


def _receive(ctx: ServiceContext, sandbox: WorkspaceRow, attack: AttackInput) -> InvoiceView:
    if attack.document is not None:
        document = attack.document
        return invoice_service.receive_document(
            ctx, sandbox, document.data, filename=document.filename, media_type=document.media_type
        )
    return invoice_service.receive_text(ctx, sandbox, attack.text or "")


def _triage(ctx: ServiceContext, text: str) -> AttackTriage | None:
    """Labels for the wall of fame only. Without the model, the attempt keeps the technique its author named."""
    try:
        return ctx.lanes.triage_attack(text)
    except LLMError:
        return None


def _hall_of_fame(ctx: ServiceContext) -> list[ChallengeAttempt]:
    rows = ctx.session.scalars(
        select(ChallengeAttemptRow)
        .order_by(ChallengeAttemptRow.creativity.desc().nulls_last(), ChallengeAttemptRow.at.desc())
        .limit(HALL_OF_FAME_SIZE)
    )
    return [_attempt(row) for row in rows]


def _attempt(row: ChallengeAttemptRow) -> ChallengeAttempt:
    return ChallengeAttempt(
        id=row.id,
        alias=row.alias,
        technique=row.technique,
        decision=Decision.model_validate(row.decision),
        broke_through=row.broke_through,
        at=row.at,
    )


def _attempt_payload(row: ChallengeAttemptRow) -> dict[str, object]:
    return {"status": row.status, "broke_through": row.broke_through, "technique": row.technique}
