import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import text

from custodio.db import Database

from .doubles import FakeAuditor
from .helpers import assert_ledger_valid, new_workspace, process


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


def test_the_summary_reports_today_the_opening_balance_and_the_autonomous_spend_of_the_month(
    client: TestClient,
) -> None:
    workspace = new_workspace(client)
    before = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()
    process(client, workspace)

    after = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    assert before["today"] == "2026-10-17"
    assert before["opening_balance"] == 100000.0
    assert before["spent_auto_base"] == 0.0
    assert after["opening_balance"] == 100000.0
    assert after["spent_auto_base"] == 1200.0  # F01, the only payment the agent made alone
    assert after["balance"] == 98800.0


def test_the_summary_carries_the_independent_auditor_report_on_the_workspace_payments(client: TestClient) -> None:
    workspace = new_workspace(client)
    before = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()
    process(client, workspace)

    after = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    assert before["audit"] == {"agrees": True, "checked": 0, "improper_payments": 0, "findings": []}
    assert after["audit"] == {"agrees": True, "checked": 1, "improper_payments": 0, "findings": []}


def test_the_summary_audit_names_every_payment_the_auditor_stopped(client: TestClient, auditor: FakeAuditor) -> None:
    workspace = new_workspace(client)
    auditor.flagged.add("F01")
    process(client, workspace)

    summary = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    audit = summary["audit"]
    assert audit["agrees"] is False
    assert audit["checked"] == 1
    assert audit["improper_payments"] == summary["metrics"]["improper_payments"] == 1
    [finding] = audit["findings"]
    assert finding["invoice_id"] == "F01"
    assert finding["severity"] == "critical"
    assert "auditor" in finding["message"]


def test_the_summary_says_whether_the_workspace_is_the_demo_or_a_company_of_its_own(client: TestClient) -> None:
    demo, blank = new_workspace(client, mode="demo"), new_workspace(client, mode="blank")

    assert client.get("/api/v1/workspaces/current", headers=demo.headers).json()["mode"] == "demo"
    assert client.get("/api/v1/workspaces/current", headers=blank.headers).json()["mode"] == "blank"
