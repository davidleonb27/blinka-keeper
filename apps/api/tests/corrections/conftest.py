import os

import pytest


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "live" in item.keywords and os.environ.get("CUSTODIO_LIVE_TESTS") != "1":
        pytest.skip("live model test: set CUSTODIO_LIVE_TESTS=1 to run it")
