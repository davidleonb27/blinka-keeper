from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from custodio.services.context import RateLimits

from .conftest import MutableClock
from .doubles import invoice_text
from .helpers import new_workspace
from .test_firewall import intent

FIVE_MIB = 5 * 1024 * 1024


@pytest.fixture
def limits() -> RateLimits:
    return RateLimits(
        model_calls_per_minute_per_ip=4,
        model_calls_per_minute_per_workspace=2,
        challenge_attempts_per_minute_per_ip=2,
        challenge_attempts_per_day=3,
    )


def upload(client: TestClient, headers: dict[str, str], number: str, ip: str = "203.0.113.7") -> int:
    response = client.post(
        "/api/v1/invoices",
        headers={**headers, "X-Forwarded-For": ip},
        data={"text": invoice_text(number=number)},
    )
    return response.status_code


def test_model_routes_are_limited_per_workspace_with_a_spanish_429(client: TestClient) -> None:
    workspace = new_workspace(client)
    assert [upload(client, workspace.headers, f"N-{i}") for i in range(2)] == [201, 201]

    response = client.post("/api/v1/invoices", headers=workspace.headers, data={"text": invoice_text(number="N-3")})

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert "Espera" in response.json()["detail"]
    assert 1 <= int(response.headers["Retry-After"]) <= 60


def test_the_window_reopens_after_a_minute(client: TestClient, clock: MutableClock) -> None:
    workspace = new_workspace(client)
    for i in range(2):
        upload(client, workspace.headers, f"W-{i}")

    clock.advance(timedelta(seconds=61))

    assert upload(client, workspace.headers, "W-9") == 201


def test_model_routes_are_limited_per_ip_across_workspaces(client: TestClient) -> None:
    first, second, third = (new_workspace(client) for _ in range(3))
    codes = [upload(client, ws.headers, f"{n}-{i}") for n, ws in enumerate((first, second)) for i in range(2)]

    assert codes == [201, 201, 201, 201]
    assert upload(client, third.headers, "IP-5") == 429
    assert upload(client, third.headers, "IP-6", ip="198.51.100.1") == 201


def test_the_firewall_is_limited_by_its_workspace(client: TestClient) -> None:
    workspace = new_workspace(client)
    codes = [
        client.post(
            "/api/v1/firewall/intents", json=intent(invoice_number=f"L-{i}"), headers=workspace.bearer
        ).status_code
        for i in range(3)
    ]

    assert codes == [200, 200, 429]


def test_routes_without_models_are_not_limited(client: TestClient) -> None:
    workspace = new_workspace(client)

    codes = {client.get("/api/v1/decisions", headers=workspace.headers).status_code for _ in range(10)}

    assert codes == {200}


def test_the_public_challenge_has_its_own_limits(client: TestClient) -> None:
    def attack(ip: str) -> int:
        response = client.post(
            "/api/v1/challenge/attempts", data={"text": invoice_text()}, headers={"X-Forwarded-For": ip}
        )
        return response.status_code

    assert [attack("192.0.2.1"), attack("192.0.2.1"), attack("192.0.2.1")] == [201, 201, 429]
    assert attack("192.0.2.2") == 201
    closed = client.post("/api/v1/challenge/attempts", data={"text": "x"}, headers={"X-Forwarded-For": "192.0.2.3"})
    assert closed.status_code == 429
    assert "reto" in closed.json()["detail"]


def test_bodies_over_the_limit_are_refused_before_any_route(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = client.post(
        "/api/v1/invoices", headers=workspace.headers, files={"file": ("big.pdf", b"x" * FIVE_MIB, "application/pdf")}
    )

    assert response.status_code == 413
    assert response.json()["code"] == "payload_too_large"
