"""The double reading with the real models. Run with CUSTODIO_LIVE_TESTS=1 uv run pytest -m live -s.

Uses the frozen L21 blind set: every invoice is read twice for real and decided by the engine. Whatever the readers
answer, an invoice whose readings do not agree is never paid alone, and nothing the blind set expects held is paid.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from custodio.contracts import CrossCheckStatus
from custodio.extraction import cross_check, second_reading

pytestmark = pytest.mark.live

SCRIPT = Path(__file__).parents[2] / "scripts" / "measure_double_reading.py"
spec = importlib.util.spec_from_file_location("measure_double_reading_live", SCRIPT)
assert spec is not None and spec.loader is not None
script = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = script
spec.loader.exec_module(script)
REAL_START = cross_check.start


@pytest.fixture(autouse=True)
def second_reader_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cross_check, "start", REAL_START)
    second_reading.read.cache_clear()


@pytest.mark.parametrize("case", script.load_blind_set(), ids=lambda case: case.id)
def test_a_real_double_reading_never_pays_what_it_should_not(case: object) -> None:
    reading = script.local_reader(case)
    assert reading.extraction is not None, reading.error
    checked = reading.extraction.cross_check
    assert checked is not None
    verdict = script.verdict_of(case, reading.extraction)
    print(case.id, checked.status.value, verdict, f"{reading.seconds:.1f}s", f"USD {reading.cost_usd:.4f}")  # type: ignore[attr-defined]
    if checked.status is not CrossCheckStatus.AGREE:
        assert verdict != "pay"
    if case.expected != "pay":  # type: ignore[attr-defined]
        assert verdict != "pay"
