import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import httpx
import pytest

from custodio.contracts import ExtractedField, ExtractedInvoice, HiddenTextFinding, HiddenTextKind, InvoiceSource
from custodio.dataset import demo_specs

SCRIPT = Path(__file__).parents[2] / "scripts" / "measure_reading.py"
API_KEY = "never-print-this-key"
WORKSPACE = "ws-test"
SEEDED = 36


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("measure_reading", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def field(value: str | None) -> ExtractedField:
    return ExtractedField(value=value, confidence=0.9, verified=value is not None)


def extraction(supplier: str, amount: str, currency: str, account: str, *, hidden: bool) -> dict[str, object]:
    findings = [HiddenTextFinding(kind=HiddenTextKind.INVISIBLE_COLOR, text="x", detail="x")] if hidden else []
    invoice = ExtractedInvoice(
        document_id="d",
        source=InvoiceSource.PDF,
        supplier_name=field(supplier),
        supplier_tax_id=field(None),
        invoice_number=field(None),
        issue_date=field(None),
        due_date=field(None),
        amount=field(amount),
        currency=field(currency),
        bank_name=field(None),
        account_number=field(account),
        description=field(None),
        visible_text="",
        hidden_findings=findings,
        reader="fake",
        overall_confidence=0.9,
    )
    return invoice.model_dump(mode="json")


class FakeProduction:
    """Answers like the deployed API: echoes each spec back, except the ones told to fail or to read wrong."""

    def __init__(self, *, refuse: int = 0, wrong_amount: int = 0, rate_limit: int = 0) -> None:
        self.specs = iter(demo_specs())
        self.refuse = refuse
        self.rate_limit = rate_limit
        self.wrong_amount = wrong_amount
        self.uploads = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/workspaces":
            assert json.loads(request.content) == {"mode": "demo"}
            return httpx.Response(201, json={"workspace_id": WORKSPACE, "api_key": API_KEY})
        assert request.headers["X-Custodio-Workspace"] == WORKSPACE
        if request.url.path == "/api/v1/workspaces/current":
            return httpx.Response(200, json={"pending_invoices": SEEDED, "metrics": {"total": 0}})
        assert request.url.path == "/api/v1/invoices"
        return self.upload()

    def upload(self) -> httpx.Response:
        self.uploads += 1
        if self.uploads <= self.rate_limit:
            return httpx.Response(429, headers={"Retry-After": "7"}, json={"code": "rate_limited"})
        spec = next(self.specs)
        if self.uploads <= self.refuse:
            return httpx.Response(503, json={"code": "reading_unavailable", "invoice_id": "i"})
        amount = spec.amount + Decimal(1) if self.uploads <= self.refuse + self.wrong_amount else spec.amount
        currency = "COP" if spec.amount_text and "$" in spec.amount_text else spec.currency
        body = extraction(
            spec.supplier_name, f"{amount:.2f}", currency, spec.account_number, hidden=bool(spec.hidden_text)
        )
        if spec.amount_text and "$" in spec.amount_text:
            body["currency"]["verified"] = False  # type: ignore[index]
        return httpx.Response(201, json={"id": "i", "read_ok": True, "extraction": body})


def measure(server: FakeProduction, *, max_uploads: int = 40, pauses: list[float] | None = None) -> dict[str, object]:
    client = httpx.Client(base_url="https://example.test/api/v1", transport=httpx.MockTransport(server))
    pause = pauses.append if pauses is not None else lambda _: None
    report: dict[str, object] = load_script().measure(client, max_uploads=max_uploads, pause=pause)
    return report


def test_every_golden_document_is_uploaded_once() -> None:
    server = FakeProduction()

    report = measure(server)

    assert server.uploads == report["uploads"] == len(demo_specs())
    assert report["read"] == len(demo_specs())
    assert report["rejected"] == {}


def test_counts_hits_per_field_rejections_and_hidden_text() -> None:
    report = measure(FakeProduction(refuse=2, wrong_amount=3))

    read = len(demo_specs()) - 2
    assert report["rejected"] == {"503 reading_unavailable": 2}
    assert report["read"] == read
    assert report["fields_correct"] == {
        "supplier_name": read,
        "amount": read - 3,
        "currency": read,
        "account_number": read,
    }
    assert report["documents_all_four_correct"] == read - 3
    hidden = sum(1 for spec in demo_specs()[2:] if spec.hidden_text)
    assert report["hidden_text"] == {"expected": hidden, "detected": hidden, "findings_on_clean_documents": 0}


def test_stops_at_the_upload_cap() -> None:
    server = FakeProduction()

    report = measure(server, max_uploads=5)

    assert server.uploads == report["uploads"] == 5


def test_waits_between_uploads_to_stay_under_the_rate_limit() -> None:
    pauses: list[float] = []

    measure(FakeProduction(), max_uploads=4, pauses=pauses)

    assert pauses == [load_script().SECONDS_BETWEEN_UPLOADS] * 3


def test_a_rate_limited_upload_waits_the_advertised_time_and_counts_against_the_cap() -> None:
    pauses: list[float] = []
    server = FakeProduction(rate_limit=2)

    report = measure(server, max_uploads=5, pauses=pauses)

    assert report["rate_limited"] == 2
    assert report["uploads"] == server.uploads == 5
    assert report["documents"] == report["read"] == 3
    assert pauses[:2] == [7.0, load_script().SECONDS_BETWEEN_UPLOADS]


def test_refuses_a_cap_above_forty_uploads() -> None:
    with pytest.raises(SystemExit):
        load_script().main(["--max-uploads", "41"])


def test_the_report_counts_the_seeded_golden_invoices_and_never_the_credentials() -> None:
    report = measure(FakeProduction())

    assert report["seeded_invoices"] == SEEDED
    assert "golden_metrics" not in report
    assert API_KEY not in json.dumps(report)
    assert WORKSPACE not in json.dumps(report)
