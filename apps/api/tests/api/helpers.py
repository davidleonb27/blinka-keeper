from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient


@dataclass(frozen=True)
class Workspace:
    id: str
    api_key: str

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Custodio-Workspace": self.id}

    @property
    def bearer(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


def new_workspace(client: TestClient, mode: str = "demo") -> Workspace:
    response = client.post("/api/v1/workspaces", json={"mode": mode})
    assert response.status_code == 201, response.text
    body = response.json()
    return Workspace(id=body["workspace_id"], api_key=body["api_key"])


def upload_text(client: TestClient, workspace: Workspace, text: str) -> dict[str, Any]:
    response = client.post("/api/v1/invoices", headers=workspace.headers, data={"text": text})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def process(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    response = client.post("/api/v1/invoices/process", headers=workspace.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def statuses(batch: dict[str, Any]) -> dict[str, str]:
    return {decision["invoice_id"]: decision["status"] for decision in batch["batch"]["decisions"]}


def assert_ledger_valid(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    response = client.get("/api/v1/ledger/verify", headers=workspace.headers)
    assert response.status_code == 200, response.text
    verification: dict[str, Any] = response.json()
    assert verification["valid"] is True, verification
    assert verification["first_broken_seq"] is None
    return verification
