from fastapi.testclient import TestClient

from .helpers import assert_ledger_valid, new_workspace


def test_the_policy_starts_as_the_seeded_version(client: TestClient) -> None:
    workspace = new_workspace(client)

    policy = client.get("/api/v1/policy", headers=workspace.headers).json()

    assert policy["version"] == 1
    assert [b["id"] for b in policy["beneficiaries"]] == ["B-NUBE", "B-ARRIENDO"]


def test_applying_a_policy_creates_a_new_version_in_the_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)
    policy = client.get("/api/v1/policy", headers=workspace.headers).json()

    response = client.put(
        "/api/v1/policy", headers=workspace.headers, json={**policy, "version": 77, "approval_threshold": 3000}
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2  # the server numbers versions, not the client
    assert client.get("/api/v1/policy", headers=workspace.headers).json()["approval_threshold"] == 3000.0
    last = client.get("/api/v1/ledger", headers=workspace.headers).json()[-1]
    assert last["kind"] == "policy_changed"
    assert last["payload"]["version"] == 2
    assert last["payload"]["changed_fields"] == ["approval_threshold"]
    assert_ledger_valid(client, workspace)


def test_a_policy_with_negative_amounts_is_refused(client: TestClient) -> None:
    workspace = new_workspace(client)
    policy = client.get("/api/v1/policy", headers=workspace.headers).json()

    response = client.put("/api/v1/policy", headers=workspace.headers, json={**policy, "reserve": -1})

    assert response.status_code == 422
    assert response.json()["code"] == "policy_invalid"


def test_a_policy_with_unknown_fields_is_refused(client: TestClient) -> None:
    workspace = new_workspace(client)
    policy = client.get("/api/v1/policy", headers=workspace.headers).json()

    response = client.put("/api/v1/policy", headers=workspace.headers, json={**policy, "pay_everything": True})

    assert response.status_code == 422


def test_a_policy_change_in_one_workspace_does_not_touch_another(client: TestClient) -> None:
    first, second = new_workspace(client), new_workspace(client)
    policy = client.get("/api/v1/policy", headers=first.headers).json()

    client.put("/api/v1/policy", headers=first.headers, json={**policy, "approval_threshold": 1})

    assert client.get("/api/v1/policy", headers=second.headers).json()["approval_threshold"] == 5000.0
