"""The live red team. The attacker is lane L3's; the judge is this API's real pipeline.

Attacks land in a sandbox cloned from the visitor's company (same rules, balance and history), so a run never touches
the visitor's panel; each verdict is also written to the visitor's ledger. Every round commits on its own, so what was
streamed is what was recorded, even if a run stops halfway.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from custodio.contracts import AttackSpec, CompanyState, Decision, LedgerKind, Policy, RedTeamEvent
from custodio.db.models import RedTeamRunRow
from custodio.llm import LLMError
from custodio.services import invoice_service, ledger_service, policy_service, records, workspace_service
from custodio.services.context import Runtime
from custodio.services.errors import model_failure
from custodio.services.workspace_service import WorkspaceKind, new_id

MAX_ROUNDS = 12


@dataclass
class _Run:
    id: str
    workspace_id: str
    sandbox_id: str
    state: CompanyState
    policy: Policy
    attacks: int = 0
    caught: int = 0


def run(runtime: Runtime, workspace_id: str, rounds: int) -> Iterator[RedTeamEvent]:
    current = _start(runtime, workspace_id, rounds)

    def judge(attack: AttackSpec) -> Decision:
        return _judge(runtime, current, attack)

    try:
        for event in runtime.lanes.red_team(current.policy, current.state, rounds=rounds, judge=judge):
            if event.type == "verdict":
                _record_verdict(runtime, current, event)
            yield event
    except LLMError as error:
        _finish(runtime, current, "failed")
        yield RedTeamEvent(type="error", round=current.attacks + 1, message=model_failure(error).message)
        return
    _finish(runtime, current, "finished")


def attack_document(attack: AttackSpec) -> str:
    """The attack as the text the reader receives. Hidden text travels with it, so the reader can catch it."""
    return attack.invoice_text if attack.hidden_text is None else f"{attack.invoice_text}\n{attack.hidden_text}"


def _start(runtime: Runtime, workspace_id: str, rounds: int) -> _Run:
    with runtime.database.session() as session:
        ctx = runtime.context(session)
        state = records.company_state(ctx, workspace_service.get(ctx, workspace_id))
        policy = policy_service.current(ctx, workspace_id)
        sandbox_id = workspace_service.create_sandbox(ctx, WorkspaceKind.REDTEAM, state, policy)
        run_row = RedTeamRunRow(
            id=new_id(),
            workspace_id=workspace_id,
            sandbox_workspace_id=sandbox_id,
            rounds=rounds,
            attacks=0,
            caught=0,
            status="running",
            started_at=ctx.now(),
            finished_at=None,
        )
        session.add(run_row)
    return _Run(id=run_row.id, workspace_id=workspace_id, sandbox_id=sandbox_id, state=state, policy=policy)


def _judge(runtime: Runtime, current: _Run, attack: AttackSpec) -> Decision:
    with runtime.database.session() as session:
        ctx = runtime.context(session)
        sandbox = workspace_service.get_sandbox(ctx, current.sandbox_id)
        received = invoice_service.receive_text(ctx, sandbox, attack_document(attack))
        outcome = invoice_service.decide(ctx, sandbox, [records.invoice(ctx, sandbox.id, received.id)])
        return outcome.batch.decisions[0]


def _record_verdict(runtime: Runtime, current: _Run, event: RedTeamEvent) -> None:
    current.attacks += 1
    current.caught += bool(event.caught)
    payload = {
        "run_id": current.id,
        "round": event.round,
        "technique": event.attack.technique if event.attack else None,
        "status": event.decision.status.value if event.decision else None,
        "caught": event.caught,
    }
    with runtime.database.session() as session:
        ledger_service.append(
            runtime.context(session), current.workspace_id, LedgerKind.REDTEAM_ATTACK, current.id, payload
        )


def _finish(runtime: Runtime, current: _Run, status: str) -> None:
    with runtime.database.session() as session:
        run_row = session.get(RedTeamRunRow, current.id)
        if run_row is not None:
            run_row.attacks, run_row.caught, run_row.status = current.attacks, current.caught, status
            run_row.finished_at = runtime.clock()
