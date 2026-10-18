import os

import pytest

from custodio.extraction import cross_check, second_reading


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "live" in item.keywords and os.environ.get("CUSTODIO_LIVE_TESTS") != "1":
        pytest.skip("live model test: set CUSTODIO_LIVE_TESTS=1 to run it")


@pytest.fixture(autouse=True)
def configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests stand a double in for Claude, so they run as a deployment with a key (never a real one offline)."""
    if "ANTHROPIC_API_KEY" not in os.environ:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-doubles")


@pytest.fixture(autouse=True)
def no_second_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most tests here are about the first reading; tests/extraction/test_second_reading.py turns the second one on."""
    second_reading.read.cache_clear()
    monkeypatch.setattr(cross_check, "start", lambda document: None)
