import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import text

from custodio.db import Database

from .helpers import assert_ledger_valid, new_workspace


def test_a_demo_workspace_starts_with_the_demo_company_and_its_pending_invoices(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = client.get("/api/v1/workspaces/current", headers=workspace.headers)

    assert response.status_code == 200
    body = response.json()
    assert body["workspace_id"] == workspace.id
    assert body["company_name"] == "Cobalto Labs, Inc."
    assert body["balance"] == 100000.0
    assert body["pending_invoices"] == 3
    assert body["metrics"]["total"] == 0
    assert body["policy_version"] == 1


def test_a_blank_workspace_has_no_invoices_and_the_default_policy(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    body = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    assert body["pending_invoices"] == 0
    assert body["balance"] == 0.0


def test_every_workspace_gets_its_own_id_and_key(client: TestClient) -> None:
    first, second = new_workspace(client), new_workspace(client)

    assert first.id != second.id
    assert first.api_key != second.api_key
    assert first.api_key.startswith("cus_")


def test_the_api_key_is_stored_only_as_its_sha256(client: TestClient, database: Database) -> None:
    workspace = new_workspace(client)

    with database.engine.connect() as connection:
        stored = connection.execute(text("select api_key_hash from workspaces")).scalars().all()

    assert stored == [hashlib.sha256(workspace.api_key.encode()).hexdigest()]


def test_an_unknown_mode_is_rejected_with_a_spanish_message(client: TestClient) -> None:
    response = client.post("/api/v1/workspaces", json={"mode": "evil"})

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert "solicitud" in response.json()["detail"]


def test_the_workspace_header_is_required(client: TestClient) -> None:
    response = client.get("/api/v1/workspaces/current")

    assert response.status_code == 400
    assert response.json()["code"] == "workspace_header_missing"


def test_an_unknown_workspace_gets_a_uniform_404(client: TestClient) -> None:
    response = client.get("/api/v1/workspaces/current", headers={"X-Custodio-Workspace": "does-not-exist"})

    assert response.status_code == 404
    assert response.json() == {"detail": "No encontramos ese espacio de trabajo.", "code": "workspace_not_found"}


def test_seeding_is_recorded_in_a_verifiable_ledger(client: TestClient) -> None:
    workspace = new_workspace(client)

    verification = assert_ledger_valid(client, workspace)

    assert verification["length"] == 4  # policy v1 + three received invoices
