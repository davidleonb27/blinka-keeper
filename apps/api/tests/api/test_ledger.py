import itertools

from fastapi.testclient import TestClient

from .helpers import assert_ledger_valid, new_workspace, process

APPROVER = {"approver": "Ana Gómez"}


def test_the_ledger_lists_entries_chained_from_genesis(client: TestClient) -> None:
    workspace = new_workspace(client)

    entries = client.get("/api/v1/ledger", headers=workspace.headers).json()

    assert [entry["seq"] for entry in entries] == [1, 2, 3, 4]
    assert entries[0]["prev_hash"] == "0" * 64
    assert all(entry["prev_hash"] == prior["hash"] for prior, entry in itertools.pairwise(entries))
    assert entries[0]["kind"] == "policy_changed"


def test_every_flow_leaves_a_verifiable_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    client.post("/api/v1/decisions/F02/approve", headers=workspace.headers, json=APPROVER)

    verification = assert_ledger_valid(client, workspace)
    kinds = [entry["kind"] for entry in client.get("/api/v1/ledger", headers=workspace.headers).json()]

    assert kinds.count("decision") == 3
    assert kinds.count("payment") == 2
    assert kinds.count("approval") == 1
    assert verification["head_hash"] == client.get("/api/v1/ledger", headers=workspace.headers).json()[-1]["hash"]


def test_the_tamper_demo_breaks_a_copy_and_never_the_real_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    response = client.post("/api/v1/ledger/tamper-demo", headers=workspace.headers, json={"seq": 3})

    assert response.status_code == 200
    demo = response.json()
    assert demo["altered_seq"] == 3
    assert demo["tampered"]["valid"] is False
    assert demo["tampered"]["first_broken_seq"] == 3
    assert demo["real"]["valid"] is True
    assert_ledger_valid(client, workspace)


def test_the_tamper_demo_defaults_to_the_latest_entry(client: TestClient) -> None:
    workspace = new_workspace(client)

    demo = client.post("/api/v1/ledger/tamper-demo", headers=workspace.headers, json={}).json()

    assert demo["altered_seq"] == 4
    assert demo["tampered"]["first_broken_seq"] == 4


def test_the_tamper_demo_rejects_a_seq_outside_the_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = client.post("/api/v1/ledger/tamper-demo", headers=workspace.headers, json={"seq": 99})

    assert response.status_code == 404


def test_ledgers_are_per_workspace(client: TestClient) -> None:
    busy, quiet = new_workspace(client), new_workspace(client, mode="blank")
    process(client, busy)

    quiet_entries = client.get("/api/v1/ledger", headers=quiet.headers).json()

    assert [entry["kind"] for entry in quiet_entries] == ["policy_changed"]
    assert_ledger_valid(client, busy)
    assert_ledger_valid(client, quiet)
