"""A stand-in for Stripe's HTTP API, under the official SDK.

The rail talks to a real `stripe.StripeClient`; only the transport is fake. So the tests exercise the SDK's own
parameter encoding, Idempotency-Key header and error parsing. Like Stripe, the fake replays the stored response of
an idempotency key it has already seen, errors included.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlsplit

import stripe

TEST_KEY = "sk_test_custodio_fake_0123456789"
Response = tuple[int, dict[str, Any]]


@dataclass(frozen=True)
class StripeRequest:
    method: str
    path: str
    idempotency_key: str | None
    form: dict[str, str]


@dataclass
class FakeStripe(stripe.HTTPClient):
    name: ClassVar[str] = "fake"

    balance_cents: int = 100_000_000
    requests: list[StripeRequest] = field(default_factory=list)
    failures: dict[str, list[Response]] = field(default_factory=dict)  # path -> responses to give before working
    unreachable: bool = False
    _replays: dict[str, Response] = field(default_factory=dict)
    _ids: int = 0

    def __post_init__(self) -> None:
        super().__init__()

    def client(self, api_key: str = TEST_KEY) -> stripe.StripeClient:
        return stripe.StripeClient(api_key, http_client=self, max_network_retries=0)

    def fail_next(self, path: str, status: int, error_type: str, code: str, message: str = "Rejected") -> None:
        error = {"error": {"type": error_type, "code": code, "message": message}}
        self.failures.setdefault(path, []).append((status, error))

    def posts(self, path: str) -> list[StripeRequest]:
        return [r for r in self.requests if r.method == "post" and r.path == path]

    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None,
        post_data: Any = None,
        *,
        _usage: list[str] | None = None,
    ) -> tuple[str, int, Mapping[str, str]]:
        if self.unreachable:
            raise stripe.APIConnectionError("Network unreachable")
        body = post_data.decode() if isinstance(post_data, bytes) else post_data or ""
        form = {key: values[0] for key, values in parse_qs(body).items()}
        key = (headers or {}).get("Idempotency-Key")
        request = StripeRequest(method=method.lower(), path=urlsplit(url).path, idempotency_key=key, form=form)
        self.requests.append(request)
        if key is not None and key in self._replays:
            status, payload = self._replays[key]
        else:
            status, payload = self._answer(request)
            if key is not None:
                self._replays[key] = (status, payload)
        return json.dumps(payload), status, {"request-id": "req_fake"}

    def close(self) -> None:
        return None

    def _answer(self, request: StripeRequest) -> Response:
        pending = self.failures.get(request.path)
        if pending:
            return pending.pop(0)
        if request.path == "/v1/balance":
            return 200, {"object": "balance", "available": [{"amount": self.balance_cents, "currency": "usd"}]}
        if request.path == "/v1/accounts":
            return 200, {"id": self._new_id("acct"), "object": "account"}
        if request.path == "/v1/payment_intents":
            self.balance_cents += int(request.form["amount"])
            return 200, {"id": self._new_id("pi"), "object": "payment_intent", "status": "succeeded"}
        if request.path == "/v1/transfers":
            return self._transfer(int(request.form["amount"]))
        return 404, {"error": {"type": "invalid_request_error", "message": f"Unknown path {request.path}"}}

    def _transfer(self, amount: int) -> Response:
        if amount > self.balance_cents:
            message = "You have insufficient available funds in your Stripe account."
            return 400, {"error": {"type": "invalid_request_error", "code": "balance_insufficient", "message": message}}
        self.balance_cents -= amount
        return 200, {"id": self._new_id("tr"), "object": "transfer", "amount": amount, "livemode": False}

    def _new_id(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}_fake{self._ids:04d}"
