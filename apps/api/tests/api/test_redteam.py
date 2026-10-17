import json
from typing import Any

from fastapi.testclient import TestClient

from custodio.services.lanes import Lanes

from .doubles import failing
from .helpers import Workspace, assert_ledger_valid, new_workspace


def run(client: TestClient, workspace: Workspace, rounds: int) -> list[dict[str, Any]]:
    response = client.post("/api/v1/redteam/runs", headers=workspace.headers, json={"rounds": rounds})
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return [json.loads(line[len("data: ") :]) for line in response.text.splitlines() if line.startswith("data: ")]


def test_rounds_stream_live_and_every_attack_is_judged_by_the_engine(client: TestClient) -> None:
    workspace = new_workspace(client)

    events = run(client, workspace, rounds=2)

    round_events = ["round_started", "attack_generated", "verdict", "round_finished"]
    assert [event["type"] for event in events] == round_events * 2 + ["summary"]
    verdicts = [event for event in events if event["type"] == "verdict"]
    assert all(event["caught"] is True for event in verdicts)
    assert all(event["decision"]["status"] == "hold" for event in verdicts)


def test_attacks_run_in_a_sandbox_and_are_recorded_in_the_visitor_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)

    run(client, workspace, rounds=2)

    ledger = client.get("/api/v1/ledger", headers=workspace.headers).json()
    attacks = [entry for entry in ledger if entry["kind"] == "redteam_attack"]
    assert [entry["payload"]["round"] for entry in attacks] == [1, 2]
    assert all(entry["payload"]["caught"] is True for entry in attacks)
    assert client.get("/api/v1/decisions", headers=workspace.headers).json() == []
    assert_ledger_valid(client, workspace)


def test_rounds_are_capped_at_twelve(client: TestClient) -> None:
    workspace = new_workspace(client)

    too_many = client.post("/api/v1/redteam/runs", headers=workspace.headers, json={"rounds": 13})
    none = client.post("/api/v1/redteam/runs", headers=workspace.headers, json={"rounds": 0})

    assert too_many.status_code == 422
    assert none.status_code == 422


def test_a_model_failure_ends_the_stream_with_an_honest_error(client: TestClient, lanes: Lanes) -> None:
    object.__setattr__(lanes, "red_team", failing)
    workspace = new_workspace(client)

    events = run(client, workspace, rounds=1)

    assert events[-1]["type"] == "error"
    assert "modelo" in events[-1]["message"]
