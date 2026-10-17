from typing import Any

from fastapi.testclient import TestClient

from custodio.contracts import AuditFinding, BatchResult, DecisionStatus
from custodio.services.lanes import Lanes

from .doubles import FakeAuditor, failing, invoice_text
from .helpers import assert_ledger_valid, new_workspace, process, statuses, upload_text

FOUR_MIB = 4 * 1024 * 1024


def test_uploading_text_returns_the_reading(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    invoice = upload_text(client, workspace, invoice_text(number="FV-900"))

    assert invoice["status"] == "received"
    assert invoice["extraction"]["invoice_number"]["value"] == "FV-900"
    assert invoice["extraction"]["source"] == "text"


def test_uploading_a_file_reads_the_document(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")
    document = invoice_text(number="FV-901").encode()

    response = client.post(
        "/api/v1/invoices",
        headers=workspace.headers,
        files={"file": ("factura.pdf", document, "application/pdf")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["extraction"]["source"] == "pdf"
    assert response.json()["document_id"]


def test_an_upload_needs_a_file_or_a_text(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    response = client.post("/api/v1/invoices", headers=workspace.headers, data={})

    assert response.status_code == 422
    assert response.json()["code"] == "invoice_input_missing"


def test_an_unsupported_media_type_is_refused(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    response = client.post(
        "/api/v1/invoices", headers=workspace.headers, files={"file": ("x.exe", b"MZ", "application/x-msdownload")}
    )

    assert response.status_code == 415


def test_a_document_over_four_mib_is_refused_with_413(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    response = client.post(
        "/api/v1/invoices",
        headers=workspace.headers,
        files={"file": ("big.pdf", b"x" * (FOUR_MIB + 1), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"


def test_processing_decides_every_pending_invoice_and_audits_it(client: TestClient) -> None:
    workspace = new_workspace(client)

    result = process(client, workspace)

    assert statuses(result) == {"F01": "paid_auto", "F02": "pending_approval", "F03": "hold"}
    assert result["audit"]["agrees"] is True
    assert result["audit"]["improper_payments"] == 0
    assert_ledger_valid(client, workspace)


def test_processing_twice_only_decides_new_invoices(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    upload_text(client, workspace, invoice_text(number="FV-500", amount="800.00"))

    second = process(client, workspace)

    assert list(statuses(second).values()) == ["paid_auto"]


def test_the_balance_and_history_carry_over_between_batches(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)
    upload_text(client, workspace, invoice_text(number="FV-001"))  # same number as the paid F01

    second = process(client, workspace)
    summary = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    assert list(statuses(second).values()) == ["hold"]
    assert summary["balance"] == 100000.0 - 1200.0


def test_metrics_count_decisions_and_accuracy_against_labels(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    metrics = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()["metrics"]

    assert metrics["total"] == 3
    assert metrics["paid_auto"] == 1
    assert metrics["hold"] == 1
    assert metrics["pending"] == 1
    assert metrics["accuracy"] == 1.0
    assert metrics["improper_payments"] == 0


def test_the_auditor_wins_and_the_payment_is_not_made(client: TestClient, auditor: FakeAuditor) -> None:
    workspace = new_workspace(client)
    auditor.flagged.add("F01")

    result = process(client, workspace)
    summary = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    f01 = next(d for d in result["batch"]["decisions"] if d["invoice_id"] == "F01")
    assert f01["status"] == "hold"
    assert "auditor" in f01["blocked_reason"]
    assert summary["balance"] == 100000.0
    assert summary["metrics"]["improper_payments"] == 1  # stopped by the auditor, never paid
    assert_ledger_valid(client, workspace)


def test_a_critical_finding_on_the_whole_batch_stops_every_payment(client: TestClient, auditor: FakeAuditor) -> None:
    workspace = new_workspace(client)
    auditor.batch_findings.append(
        AuditFinding(invoice_id="saldo", severity="critical", message="Los pagos aprobados tocan la reserva.")
    )

    result = process(client, workspace)
    summary = client.get("/api/v1/workspaces/current", headers=workspace.headers).json()

    f01 = next(d for d in result["batch"]["decisions"] if d["invoice_id"] == "F01")
    assert f01["status"] == "hold"
    assert "auditor" in f01["blocked_reason"]
    assert result["vetoed"] == ["F01"]
    assert summary["balance"] == 100000.0
    assert_ledger_valid(client, workspace)


def test_when_the_reader_fails_the_invoice_waits_for_a_person(client: TestClient, lanes: Lanes) -> None:
    workspace = new_workspace(client, mode="blank")
    object.__setattr__(lanes, "extract_text", failing)

    response = client.post("/api/v1/invoices", headers=workspace.headers, data={"text": "Factura borrosa"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "reading_unavailable"
    assert "revisión humana" in body["detail"]
    assert statuses(process(client, workspace)) == {body["invoice_id"]: "pending_approval"}


def test_a_payment_with_a_failing_hold_rule_is_never_recorded_even_if_engine_and_auditor_miss_it(
    client: TestClient, lanes: Lanes
) -> None:
    honest = lanes.decide_all

    def sabotaged(*args: Any, **kwargs: Any) -> BatchResult:
        batch = honest(*args, **kwargs)
        paid = [d.model_copy(update={"status": DecisionStatus.PAID_AUTO}) for d in batch.decisions]
        return batch.model_copy(update={"decisions": paid})

    object.__setattr__(lanes, "decide_all", sabotaged)
    workspace = new_workspace(client)

    result = process(client, workspace)

    f03 = next(d for d in result["batch"]["decisions"] if d["invoice_id"] == "F03")  # account changed: R4 holds
    assert f03["status"] == "hold"
    assert "retención" in f03["blocked_reason"]
    assert "F03" in result["vetoed"]
    assert_ledger_valid(client, workspace)
