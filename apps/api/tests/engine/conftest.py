import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: the 20.000-example property run; skipped unless CUSTODIO_SLOW_TESTS=1")
