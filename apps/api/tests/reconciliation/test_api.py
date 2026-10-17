"""The reconciliation endpoints, end to end: upload, review, close the month and download its evidence."""

import io
import json
import zipfile
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from custodio.llm import LLMError
from custodio.reconciliation.demo import demo_statement_csv
from tests.api.conftest import MutableClock
from tests.api.helpers import Workspace, assert_ledger_valid, new_workspace, process

from .conftest import FakeStatementReader

API = "/api/v1"
REVIEWER = "Ana Gómez"


def reconcile_demo(client: TestClient, workspace: Workspace) -> dict[str, Any]:
    response = client.post(f"{API}/reconciliations", headers=workspace.headers, data={"demo": "true"})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def upload(client: TestClient, workspace: Workspace, name: str, data: bytes, media_type: str) -> Any:
    return client.post(f"{API}/reconciliations", headers=workspace.headers, files={"file": (name, data, media_type)})


def processed_demo(client: TestClient) -> Workspace:
    workspace = new_workspace(client)
    process(client, workspace)
    return workspace


def movement(body: dict[str, Any], text: str) -> dict[str, Any]:
    return next(item for item in body["movements"] if text in item["movement"]["description"])


def alerts(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in body["movements"] if item["needs_review"]]


def resolve(client: TestClient, workspace: Workspace, body: dict[str, Any], item: dict[str, Any], note: str) -> Any:
    return client.post(
        f"{API}/reconciliations/{body['id']}/resolve",
        headers=workspace.headers,
        json={"movement_id": item["movement"]["id"], "reviewer": REVIEWER, "note": note},
    )


def resolve_all(client: TestClient, workspace: Workspace, body: dict[str, Any]) -> dict[str, Any]:
    for item in alerts(body):
        response = resolve(client, workspace, body, item, "Revisado con el banco.")
        assert response.status_code == 200, response.text
        body = response.json()
    return body


def close(client: TestClient, workspace: Workspace, period: str = "2026-10") -> Any:
    return client.post(f"{API}/periods/{period}/close", headers=workspace.headers, json={"closed_by": REVIEWER})


def evidence(client: TestClient, workspace: Workspace, period: str = "2026-10") -> Any:
    return client.get(f"{API}/periods/{period}/evidence.zip", headers=workspace.headers)


def test_the_demo_statement_reconciles_the_processed_demo_batch(client: TestClient) -> None:
    workspace = processed_demo(client)

    body = reconcile_demo(client, workspace)

    assert body["period"] == "2026-10"
    assert body["source"] == "demo"
    assert body["demo_shift_days"] == 0
    assert body["summary"]["reconciled"]["count"] == 17
    assert body["summary"]["alerts_open"] == 2
    assert body["can_close"] is False
    orbit = movement(body, "ORBIT")
    assert orbit["result"]["status"] == "unmatched_outflow"
    assert orbit["needs_review"] is True
    kora = movement(body, "KORA")
    assert kora["result"]["level"] == "tolerance"
    assert kora["acta_url"] == "https://custodio.test/acta/F-001"
    assert [p["invoice_id"] for p in body["payments"] if p["status"] == "pending"] == ["F-036"]
    assert_ledger_valid(client, workspace)


def test_each_reconciliation_and_each_bank_confirmation_is_written_in_the_ledger(client: TestClient) -> None:
    workspace = processed_demo(client)
    body = reconcile_demo(client, workspace)

    ledger = client.get(f"{API}/ledger", headers=workspace.headers).json()
    acta = client.get(f"{API}/decisions/F-005", headers=workspace.headers).json()

    [summary] = [entry for entry in ledger if entry["kind"] == "reconciliation" and entry["subject_id"] == body["id"]]
    assert summary["payload"]["movements"] == 22
    assert summary["payload"]["statement_sha256"]
    assert summary["seq"] == body["ledger_seq"]
    [confirmation] = [entry for entry in acta["ledger"] if entry["kind"] == "reconciliation"]
    assert confirmation["payload"]["reconciliation_id"] == body["id"]
    assert confirmation["payload"]["level"] == "exact"


def test_a_reconciliation_is_read_back_only_from_its_workspace(client: TestClient) -> None:
    workspace = processed_demo(client)
    body = reconcile_demo(client, workspace)
    other = new_workspace(client)

    mine = client.get(f"{API}/reconciliations/{body['id']}", headers=workspace.headers)
    theirs = client.get(f"{API}/reconciliations/{body['id']}", headers=other.headers)
    listed = client.get(f"{API}/reconciliations", headers=workspace.headers).json()

    assert mine.json() == body
    assert theirs.status_code == 404
    assert [item["id"] for item in listed] == [body["id"]]
    assert listed[0]["alerts_open"] == 2


def test_the_demo_csv_uploaded_as_a_file_gives_the_same_reconciliation(client: TestClient) -> None:
    workspace = processed_demo(client)
    demo = reconcile_demo(client, workspace)
    download = client.get(f"{API}/reconciliations/demo-statement", headers=workspace.headers, params={"format": "csv"})

    uploaded = upload(client, workspace, "extracto.csv", download.content, "text/csv")

    assert download.headers["content-type"].startswith("text/csv")
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["source"] == "csv"
    assert [m["result"] for m in uploaded.json()["movements"]] == [m["result"] for m in demo["movements"]]


def test_the_demo_statement_follows_the_day_the_batch_was_paid(client: TestClient, clock: MutableClock) -> None:
    clock.advance(timedelta(days=4))
    workspace = processed_demo(client)

    body = reconcile_demo(client, workspace)

    assert body["demo_shift_days"] == 4
    assert body["summary"]["reconciled"]["count"] == 17


def test_the_demo_pdf_can_be_downloaded(client: TestClient) -> None:
    workspace = processed_demo(client)

    response = client.get(f"{API}/reconciliations/demo-statement", headers=workspace.headers, params={"format": "pdf"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_a_pdf_statement_is_read_through_the_model_lane(
    client: TestClient, statement_reader: FakeStatementReader
) -> None:
    workspace = processed_demo(client)

    response = upload(client, workspace, "extracto.pdf", b"%PDF-1.4 demo", "application/pdf")

    assert response.status_code == 201, response.text
    assert response.json()["reader"] == "pdfplumber+claude-sonnet-5-5"
    assert response.json()["source"] == "document"
    assert statement_reader.calls == [
        {"filename": "extracto.pdf", "media_type": "application/pdf", "default_currency": "USD"}
    ]


def test_a_model_failure_reads_nothing_and_says_so(client: TestClient, statement_reader: FakeStatementReader) -> None:
    workspace = processed_demo(client)
    statement_reader.error = LLMError("sin respuesta")

    response = upload(client, workspace, "extracto.png", b"\x89PNG", "image/png")

    assert response.status_code == 503
    assert response.json()["code"] == "model_unavailable"
    assert client.get(f"{API}/reconciliations", headers=workspace.headers).json() == []


def test_files_that_are_not_statements_are_refused_with_a_reason(client: TestClient) -> None:
    workspace = processed_demo(client)

    unsupported = upload(client, workspace, "extracto.xlsx", b"PK\x03\x04", "application/vnd.ms-excel.sheet")
    not_a_statement = upload(client, workspace, "lista.csv", b"Nombre;Ciudad\nAna;Bogota\n", "text/csv")
    nothing = client.post(f"{API}/reconciliations", headers=workspace.headers, data={})

    assert unsupported.status_code == 415
    assert not_a_statement.status_code == 422
    assert "fecha" in not_a_statement.json()["detail"]
    assert nothing.status_code == 422


def test_the_fx_tolerance_is_set_per_reconciliation(client: TestClient) -> None:
    workspace = processed_demo(client)

    strict = client.post(
        f"{API}/reconciliations", headers=workspace.headers, data={"demo": "true", "fx_tolerance_pct": "0"}
    )

    assert strict.status_code == 201, strict.text
    assert strict.json()["settings"]["fx_tolerance_pct"] == 0
    assert strict.json()["summary"]["differences"]["count"] == 0


def test_a_person_resolves_an_alert_with_a_note_that_stays_in_the_ledger(client: TestClient) -> None:
    workspace = processed_demo(client)
    body = reconcile_demo(client, workspace)

    response = resolve(client, workspace, body, movement(body, "ORBIT"), "Pago hecho por fuera; se pidió el reverso.")

    assert response.status_code == 200, response.text
    review = movement(response.json(), "ORBIT")["review"]
    assert review["reviewer"] == REVIEWER
    assert review["note"] == "Pago hecho por fuera; se pidió el reverso."
    entry = client.get(f"{API}/ledger", headers=workspace.headers).json()[review["ledger_seq"] - 1]
    assert entry["kind"] == "reconciliation_review"
    assert entry["payload"]["note"] == review["note"]
    assert response.json()["summary"]["alerts_open"] == 1
    assert_ledger_valid(client, workspace)


def test_only_movements_that_need_it_are_resolved_and_only_once(client: TestClient) -> None:
    workspace = processed_demo(client)
    body = reconcile_demo(client, workspace)
    resolve(client, workspace, body, movement(body, "ORBIT"), "Revisado.")

    twice = resolve(client, workspace, body, movement(body, "ORBIT"), "Otra vez.")
    reconciled = resolve(client, workspace, body, movement(body, "PULSO"), "No hace falta.")
    blank = resolve(client, workspace, body, movement(body, "CUMULUS"), "  ")

    assert twice.status_code == 409
    assert reconciled.status_code == 409
    assert blank.status_code == 422


def test_the_month_closes_only_when_every_outflow_without_invoice_was_reviewed(client: TestClient) -> None:
    workspace = processed_demo(client)
    body = reconcile_demo(client, workspace)

    early = close(client, workspace)
    resolve_all(client, workspace, body)
    closed = close(client, workspace)
    again = close(client, workspace)

    assert early.status_code == 409
    assert "2" in early.json()["detail"]
    assert closed.status_code == 200, closed.text
    assert closed.json()["close"]["closed_by"] == REVIEWER
    assert closed.json()["close"]["reconciliation_id"] == body["id"]
    assert closed.json()["summary"]["alerts_open"] == 0
    assert again.status_code == 409
    entry = client.get(f"{API}/ledger", headers=workspace.headers).json()[closed.json()["close"]["ledger_seq"] - 1]
    assert entry["kind"] == "period_closed"
    assert client.get(f"{API}/reconciliations/{body['id']}", headers=workspace.headers).json()["period_closed"]
    assert_ledger_valid(client, workspace)


def test_a_closed_month_takes_no_more_reconciliations_or_reviews(client: TestClient) -> None:
    workspace = processed_demo(client)
    resolve_all(client, workspace, reconcile_demo(client, workspace))
    close(client, workspace)

    upload_after = client.post(f"{API}/reconciliations", headers=workspace.headers, data={"demo": "true"})

    assert upload_after.status_code == 409


def test_a_month_without_a_statement_cannot_close(client: TestClient) -> None:
    workspace = processed_demo(client)

    response = close(client, workspace, "2026-09")
    malformed = close(client, workspace, "2026-13")

    assert response.status_code == 409
    assert malformed.status_code == 422


def test_the_evidence_pack_is_for_closed_months_and_is_reproducible(client: TestClient, clock: MutableClock) -> None:
    workspace = processed_demo(client)
    body = resolve_all(client, workspace, reconcile_demo(client, workspace))
    before = evidence(client, workspace)
    close(client, workspace)

    first = evidence(client, workspace)
    clock.advance(timedelta(hours=3))
    second = evidence(client, workspace)

    assert before.status_code == 409
    assert first.status_code == 200
    assert first.headers["content-type"] == "application/zip"
    assert "custodio-cierre-2026-10.zip" in first.headers["content-disposition"]
    one, two = zipfile.ZipFile(io.BytesIO(first.content)), zipfile.ZipFile(io.BytesIO(second.content))
    assert {n for n in one.namelist() if one.read(n) != two.read(n)} == {"manifiesto.json"}
    assert "actas/F-005.json" in one.namelist()
    assert json.loads(one.read("registro/verificacion.json"))["valid"] is True
    acta = json.loads(one.read("actas/F-005.json"))
    assert acta["decision"]["status"] == "paid_auto"
    assert any(entry["kind"] == "reconciliation" for entry in acta["registro"])
    assert body["id"] in one.read("manifiesto.json").decode()


def test_an_unprocessed_workspace_still_reconciles_and_flags_every_outflow(client: TestClient) -> None:
    workspace = new_workspace(client)

    body = reconcile_demo(client, workspace)

    assert body["summary"]["reconciled"]["count"] == 0
    assert body["summary"]["alerts_open"] == 19  # 18 transfers and the duplicate; fees and the deposit are not alerts
    download = client.get(f"{API}/reconciliations/demo-statement", headers=workspace.headers, params={"format": "csv"})
    assert download.content == demo_statement_csv()
