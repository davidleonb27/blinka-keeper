from fastapi.testclient import TestClient

from custodio.services.lanes import Lanes

from .doubles import FakeAuditor, failing, invoice_text
from .helpers import new_workspace

CHANGED_ACCOUNT = invoice_text(number="RB-1", account="123123123")
LEGITIMATE = invoice_text(number="RB-2", amount="900.00")


def attempt(client: TestClient, text: str, **fields: str) -> dict[str, object]:
    response = client.post("/api/v1/challenge/attempts", data={"text": text, **fields})
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def test_an_attack_is_judged_by_the_full_pipeline_and_caught(client: TestClient) -> None:
    result = attempt(client, CHANGED_ACCOUNT, alias="mallory")

    assert result["broke_through"] is False
    assert result["alias"] == "mallory"
    assert result["technique"] == "Cuenta cambiada"
    decision = result["decision"]
    assert isinstance(decision, dict)
    assert decision["status"] == "hold"


def test_an_attack_can_be_uploaded_as_a_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/challenge/attempts", files={"file": ("trampa.pdf", CHANGED_ACCOUNT.encode(), "application/pdf")}
    )

    assert response.status_code == 201
    assert response.json()["decision"]["status"] == "hold"


def test_an_attempt_needs_a_text_or_a_file(client: TestClient) -> None:
    assert client.post("/api/v1/challenge/attempts", data={"alias": "x"}).status_code == 422


def test_attempts_never_touch_visitor_workspaces(client: TestClient) -> None:
    workspace = new_workspace(client)
    before = client.get("/api/v1/ledger", headers=workspace.headers).json()

    attempt(client, CHANGED_ACCOUNT)

    assert client.get("/api/v1/ledger", headers=workspace.headers).json() == before
    assert client.get("/api/v1/workspaces/current", headers=workspace.headers).json()["pending_invoices"] == 3


def test_the_stats_count_every_attempt_honestly(client: TestClient) -> None:
    attempt(client, CHANGED_ACCOUNT, alias="a")
    attempt(client, LEGITIMATE, alias="b")
    attempt(client, invoice_text(number="RB-3", amount="7000.00"), alias="c")

    stats = client.get("/api/v1/challenge/stats").json()

    assert stats["attempts"] == 3
    assert stats["held"] == 1
    assert stats["escalated"] == 1
    assert stats["paid_legitimately"] == 1
    assert stats["improper_payments"] == 0
    assert len(stats["hall_of_fame"]) == 3


def test_broke_through_only_when_the_auditor_rejects_a_payment(client: TestClient, auditor: FakeAuditor) -> None:
    auditor.flag_every_payment = True

    result = attempt(client, LEGITIMATE)
    stats = client.get("/api/v1/challenge/stats").json()

    assert result["broke_through"] is True
    decision = result["decision"]
    assert isinstance(decision, dict)
    assert decision["status"] == "hold"  # the auditor stopped the money anyway
    assert stats["improper_payments"] == 1


def test_a_failed_triage_still_records_the_attempt(client: TestClient, lanes: Lanes) -> None:
    object.__setattr__(lanes, "triage_attack", failing)

    result = attempt(client, CHANGED_ACCOUNT, technique="Mi técnica")

    assert result["technique"] == "Mi técnica"
    assert client.get("/api/v1/challenge/stats").json()["attempts"] == 1
