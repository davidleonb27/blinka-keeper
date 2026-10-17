"""Two writers on the same workspace must both land on the chain, never collide on (workspace_id, seq)."""

import threading

import pytest
from fastapi.testclient import TestClient

from custodio.contracts import LedgerKind
from custodio.services import ledger_service
from custodio.services.context import Runtime

from .helpers import assert_ledger_valid, new_workspace

WAIT_SECONDS = 10
HEAD_READ_GRACE_SECONDS = 0.3


def test_a_writer_that_read_a_stale_head_still_appends_after_the_other_commits(
    client: TestClient, runtime: Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = new_workspace(client)
    stale_head_read = threading.Event()
    original_head = ledger_service._head

    def head_then_signal(ctx: object, workspace_id: str) -> object:
        head = original_head(ctx, workspace_id)  # type: ignore[arg-type]
        if threading.current_thread().name == "late-writer":
            stale_head_read.set()
        return head

    monkeypatch.setattr(ledger_service, "_head", head_then_signal)
    errors: list[BaseException] = []

    def late_writer() -> None:
        try:
            with runtime.database.session() as session:
                ledger_service.append(runtime.context(session), workspace.id, LedgerKind.DECISION, "late", {"n": 2})
        except BaseException as error:  # the thread's failure must reach the test
            errors.append(error)

    with runtime.database.session() as session:
        ledger_service.append(runtime.context(session), workspace.id, LedgerKind.DECISION, "early", {"n": 1})
        thread = threading.Thread(target=late_writer, name="late-writer")
        thread.start()
        assert stale_head_read.wait(WAIT_SECONDS)
        thread.join(HEAD_READ_GRACE_SECONDS)  # the late writer is now blocked on its insert
    thread.join(WAIT_SECONDS)

    assert errors == []
    entries = client.get("/api/v1/ledger", headers=workspace.headers).json()
    assert [entry["subject_id"] for entry in entries[-2:]] == ["early", "late"]
    assert_ledger_valid(client, workspace)
