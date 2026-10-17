"""A deployment without ANTHROPIC_API_KEY: the engine, the auditor, the ledger, the firewall and the reading of text
documents keep working with the real lanes; what needs the model answers that it requires the key."""

import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from custodio.api.app import create_app
from custodio.db import Database
from custodio.services.context import Runtime
from custodio.services.lanes import production_lanes

from .conftest import GENEROUS, MutableClock
from .helpers import new_workspace

KEY_REQUIRED = "requiere ANTHROPIC_API_KEY"
PULSO_INTENT = {
    "agent": "erp-bot",
    "beneficiary_name": "Pulso Software Inc.",
    "beneficiary_tax_id": "84-2219034",
    "bank_name": "Mercury",
    "account_number": "2214-1180",
    "amount": 840,
    "currency": "USD",
    "invoice_number": "PS-90001",
    "issue_date": "2026-10-15",
    "description": "Licencias de software",
}


def tiny_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def keyless(database: Database, clock: MutableClock, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    runtime = Runtime(
        database=database,
        lanes=production_lanes(),
        clock=clock,
        limits=GENEROUS,
        public_base_url="https://custodio.test",
    )
    with TestClient(create_app(runtime)) as client:
        yield client


def test_health_says_the_model_is_not_configured(keyless: TestClient) -> None:
    assert keyless.get("/api/v1/health").json()["anthropic"] is False


def test_the_firewall_reads_and_decides_an_intent_without_the_model(keyless: TestClient) -> None:
    workspace = new_workspace(keyless)

    response = keyless.post("/api/v1/firewall/intents", json=PULSO_INTENT, headers=workspace.bearer)

    assert response.status_code == 200, response.text
    decision = response.json()["decision"]
    reading = next(rule for rule in decision["rules"] if rule["rule_id"] == "R1")
    assert reading["outcome"] == "pass"
    assert decision["agent_verdict"] in {"pay", "hold", "escalate"}
    assert keyless.get("/api/v1/ledger/verify", headers=workspace.headers).json()["valid"] is True


def test_the_firewall_still_holds_a_changed_account_without_the_model(keyless: TestClient) -> None:
    workspace = new_workspace(keyless)
    changed = {**PULSO_INTENT, "account_number": "9999-0000", "invoice_number": "PS-90002"}

    response = keyless.post("/api/v1/firewall/intents", json=changed, headers=workspace.bearer)

    assert response.status_code == 200, response.text
    assert response.json()["decision"]["agent_verdict"] == "hold"


def test_compiling_rules_answers_that_it_requires_the_key(keyless: TestClient) -> None:
    workspace = new_workspace(keyless)

    response = keyless.post(
        "/api/v1/policy/compile", json={"text": "Nada sobre 3.000 USD sin Ana"}, headers=workspace.headers
    )

    assert response.status_code == 503
    assert response.json()["code"] == "model_not_configured"
    assert KEY_REQUIRED in response.json()["detail"]


def test_an_image_answers_that_it_requires_the_key_and_stores_nothing(keyless: TestClient) -> None:
    workspace = new_workspace(keyless)
    before = keyless.get("/api/v1/ledger", headers=workspace.headers).json()

    response = keyless.post(
        "/api/v1/invoices",
        headers=workspace.headers,
        files={"file": ("factura.png", tiny_png(), "image/png")},
    )

    assert response.status_code == 503
    assert KEY_REQUIRED in response.json()["detail"]
    assert keyless.get("/api/v1/ledger", headers=workspace.headers).json() == before
