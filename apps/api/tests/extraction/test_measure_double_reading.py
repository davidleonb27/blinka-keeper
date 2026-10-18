import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest

from custodio.dataset import load_demo
from custodio.dataset.reading import read_spec

SCRIPT = Path(__file__).parents[2] / "scripts" / "measure_double_reading.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("measure_double_reading", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up while the script loads
    spec.loader.exec_module(module)
    return module


script = load_script()


@pytest.mark.parametrize(
    ("successes", "trials", "low", "high"),
    [(20, 20, 0.8316, 1.0), (0, 20, 0.0, 0.1684), (18, 20, 0.6830, 0.9877), (5, 10, 0.1871, 0.8129)],
)
def test_clopper_pearson_matches_the_published_values(successes: int, trials: int, low: float, high: float) -> None:
    got = script.clopper_pearson(successes, trials)
    assert got == pytest.approx((low, high), abs=1e-3)


def test_rule_of_three_and_percentiles() -> None:
    assert script.rule_of_three(20) == pytest.approx(0.15)
    assert script.percentile([3.0, 1.0, 2.0, 4.0], 0.5) == 2.0
    assert script.percentile([float(n) for n in range(1, 21)], 0.95) == 19.0
    assert script.percentile([], 0.5) is None


def test_the_blind_set_is_twenty_frozen_cases_across_every_channel() -> None:
    cases = script.load_blind_set()
    assert len(cases) == 20 and len({case.id for case in cases}) == 20
    assert {case.spec.channel.value for case in cases} == {"pdf", "image", "email", "whatsapp", "text"}
    assert {case.expected for case in cases} == {"pay", "hold", "escalate"}
    traps = {case.trap for case in cases}
    assert {"changed_account", "amount_in_words_mismatch", "hidden_instruction_other_language"} <= traps


def perfect_reader(case: object) -> object:
    demo = load_demo()
    extraction = read_spec(case.spec, document_id=case.id, customer=demo.state.company_name, confidence={})  # type: ignore[attr-defined]
    return script.Reading(extraction, 0.5, 0.01)


def test_a_perfect_reader_gets_every_decision_but_the_two_the_reading_must_catch() -> None:
    report = script.measure(perfect_reader, script.load_blind_set())
    assert report["invoices"] == 20
    assert report["decisions_correct"] == 18
    assert report["improper_payments"] == ["B-13", "B-17"]
    assert report["cost_usd_per_invoice"] == 0.01
    assert report["latency_seconds"] == {"p50": 0.5, "p95": 0.5}


def test_an_unreadable_upload_is_never_counted_as_paid() -> None:
    def failing(case: object) -> object:
        return script.Reading(None, 1.0, None, error="HTTP 503")

    report = script.measure(failing, script.load_blind_set())
    assert report["paid_alone"] == 0 and report["improper_payments"] == []
    assert report["cost_usd_per_invoice"] == "NO MEDIDO"


def test_the_remote_reader_drops_the_workspace_key_and_uploads_each_document() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/workspaces"):
            return httpx.Response(201, json={"workspace_id": "ws-1", "api_key": "never-print-this-key"})
        return httpx.Response(503, json={"code": "model_unavailable"})

    with httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.test/api/v1") as client:
        reader = script.remote_reader(client, pause=lambda seconds: None)
        reading = reader(script.load_blind_set()[0])
    assert reading.extraction is None and reading.error == "HTTP 503"
    assert seen[-1].headers["X-Custodio-Workspace"] == "ws-1"
    assert all("never-print-this-key" not in str(request.headers) for request in seen)
