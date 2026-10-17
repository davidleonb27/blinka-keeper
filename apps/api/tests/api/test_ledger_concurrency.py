"""Two writers on the same workspace must both land on the chain, never collide on (workspace_id, seq)."""

import threading

import pytest
from fastapi.testclient import TestClient

from custodio.contracts import LedgerKind
from custodio.services import ledger_service
from custodio.services.context import Runtime

from .doubles import invoice_text
from .helpers import assert_ledger_valid, new_workspace, upload_text

WAIT_SECONDS = 10
UPLOADERS = 8
UPLOADS_EACH = 3
GRACE_SECONDS = 0.3


def test_a_late_writer_still_appends_after_the_other_commits(
    client: TestClient, runtime: Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = new_workspace(client)
    writing = threading.Event()
    stale_head_read = threading.Event()
    original_lock, original_head = ledger_service._lock_chain, ledger_service._head

    def lock_then_signal(ctx: object, workspace_id: str) -> None:
        if threading.current_thread().name == "late-writer":
            writing.set()
        original_lock(ctx, workspace_id)  # type: ignore[arg-type]

    def head_then_signal(ctx: object, workspace_id: str) -> object:
        head = original_head(ctx, workspace_id)  # type: ignore[arg-type]
        if threading.current_thread().name == "late-writer":
            stale_head_read.set()
        return head

    monkeypatch.setattr(ledger_service, "_lock_chain", lock_then_signal)
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
        assert writing.wait(WAIT_SECONDS)
        if runtime.database.is_sqlite:  # Postgres makes the late writer wait for the lock before it reads the head
            assert stale_head_read.wait(WAIT_SECONDS)
        thread.join(GRACE_SECONDS)  # the late writer is now blocked on the lock or on its insert
    thread.join(WAIT_SECONDS)

    assert errors == []
    entries = client.get("/api/v1/ledger", headers=workspace.headers).json()
    assert [entry["subject_id"] for entry in entries[-2:]] == ["early", "late"]
    assert_ledger_valid(client, workspace)


def test_simultaneous_uploads_on_one_workspace_all_land_on_one_valid_chain(client: TestClient) -> None:
    workspace = new_workspace(client)
    before = len(client.get("/api/v1/ledger", headers=workspace.headers).json())
    start = threading.Barrier(UPLOADERS)
    errors: list[BaseException] = []

    def uploader(n: int) -> None:
        try:
            start.wait(WAIT_SECONDS)
            for i in range(UPLOADS_EACH):
                upload_text(client, workspace, invoice_text(number=f"C-{n}-{i}"))
        except BaseException as error:  # the thread's failure must reach the test
            errors.append(error)

    threads = [threading.Thread(target=uploader, args=(n,)) for n in range(UPLOADERS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(WAIT_SECONDS * 3)

    assert errors == []
    seqs = [entry["seq"] for entry in client.get("/api/v1/ledger", headers=workspace.headers).json()]
    assert len(seqs) == before + UPLOADERS * UPLOADS_EACH
    assert seqs == list(range(seqs[0], seqs[0] + len(seqs)))
    assert_ledger_valid(client, workspace)
