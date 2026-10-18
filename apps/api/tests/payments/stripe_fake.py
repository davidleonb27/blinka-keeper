"""A stand-in for Stripe's HTTP API, under the official SDK.

The rail talks to a real `stripe.StripeClient`; only the transport is fake. So the tests exercise the SDK's own
parameter encoding, Idempotency-Key header and error parsing. Like Stripe, the fake replays the stored response of
an idempotency key it has already seen, errors included.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlsplit

import stripe

TEST_KEY = "sk_test_custodio_fake_0123456789"
FIRST_CREATED = 1_792_249_200  # 2026-10-17T15:00:00Z, the API tests' clock
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
    pending_reads: int = 0  # balance reads after a top-up during which its funds are still pending, as in Stripe
    requests: list[StripeRequest] = field(default_factory=list)
    failures: dict[str, list[Response]] = field(default_factory=dict)  # path -> answers to the next POSTs
    read_failures: dict[str, list[Response]] = field(default_factory=dict)  # path -> answers to the next GETs
    unreachable: bool = False
    seconds: Callable[[], int] | None = None  # the transfers' `created`; by default one second apart from FIRST_CREATED
    transfers: list[dict[str, Any]] = field(default_factory=list)
    _replays: dict[str, Response] = field(default_factory=dict)
    _ids: int = 0
    _lost: set[str] = field(default_factory=set)
    _pending_cents: int = 0
    _reads_left: int = 0

    def __post_init__(self) -> None:
        super().__init__()

    def client(self, api_key: str = TEST_KEY) -> stripe.StripeClient:
        return stripe.StripeClient(api_key, http_client=self, max_network_retries=0)

    def lose_next_answer(self, path: str) -> None:
        """The request reaches Stripe and is carried out, but its answer never comes back."""
        self._lost.add(path)

    def fail_next(self, path: str, status: int, error_type: str, code: str, message: str = "Rejected") -> None:
        error = {"error": {"type": error_type, "code": code, "message": message}}
        self.failures.setdefault(path, []).append((status, error))

    def fail_next_read(self, path: str, status: int, error_type: str, message: str = "Rejected") -> None:
        self.read_failures.setdefault(path, []).append((status, {"error": {"type": error_type, "message": message}}))

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
        parts = urlsplit(url)
        body = post_data.decode() if isinstance(post_data, bytes) else post_data or parts.query
        form = {key: values[0] for key, values in parse_qs(body).items()}
        key = (headers or {}).get("Idempotency-Key")
        request = StripeRequest(method=method.lower(), path=parts.path, idempotency_key=key, form=form)
        self.requests.append(request)
        if key is not None and key in self._replays:
            status, payload = self._replays[key]
        else:
            status, payload = self._answer(request)
            if key is not None:
                self._replays[key] = (status, payload)
        if request.method == "post" and request.path in self._lost:
            self._lost.discard(request.path)
            raise stripe.APIConnectionError("Connection reset")
        return json.dumps(payload), status, {"request-id": "req_fake"}

    def close(self) -> None:
        return None

    def _answer(self, request: StripeRequest) -> Response:
        pending = (self.failures if request.method == "post" else self.read_failures).get(request.path)
        if pending:
            return pending.pop(0)
        if request.path == "/v1/balance":
            return 200, self._balance()
        if request.path == "/v1/accounts":
            return 200, {"id": self._new_id("acct"), "object": "account"}
        if request.path == "/v1/payment_intents":
            self._pending_cents += int(request.form["amount"])
            self._reads_left = self.pending_reads
            self._settle_if_due()
            return 200, {"id": self._new_id("pi"), "object": "payment_intent", "status": "succeeded"}
        if request.path == "/v1/transfers" and request.method == "get":
            return 200, self._list_transfers(request.form)
        if request.path.startswith("/v1/transfers/") and request.method == "get":
            return self._retrieve_transfer(request.path.rsplit("/", 1)[1], request.form)
        if request.path == "/v1/transfers":
            return self._transfer(request.form)
        return 404, {"error": {"type": "invalid_request_error", "message": f"Unknown path {request.path}"}}

    def _balance(self) -> dict[str, Any]:
        if self._reads_left > 0:
            self._reads_left -= 1
        else:
            self._settle_if_due()
        return {
            "object": "balance",
            "available": [{"amount": self.balance_cents, "currency": "usd"}],
            "pending": [{"amount": self._pending_cents, "currency": "usd"}],
        }

    def _settle_if_due(self) -> None:
        if self._reads_left == 0:
            self.balance_cents += self._pending_cents
            self._pending_cents = 0

    def add_transfer(
        self, amount: int, metadata: dict[str, str], destination: str = "acct_fake_stray"
    ) -> dict[str, Any]:
        """A transfer made outside Custodio, straight in Stripe's dashboard."""
        return self._record_transfer(amount, None, destination, metadata)

    def _transfer(self, form: dict[str, str]) -> Response:
        amount = int(form["amount"])
        if amount > self.balance_cents:
            message = "You have insufficient available funds in your Stripe account."
            return 400, {"error": {"type": "invalid_request_error", "code": "balance_insufficient", "message": message}}
        self.balance_cents -= amount
        metadata = {key[len("metadata[") : -1]: value for key, value in form.items() if key.startswith("metadata[")}
        return 200, self._record_transfer(amount, form.get("transfer_group"), form.get("destination"), metadata)

    def _record_transfer(
        self, amount: int, group: str | None, destination: str | None, metadata: dict[str, str]
    ) -> dict[str, Any]:
        transfer = {
            "id": self._new_id("tr"),
            "object": "transfer",
            "amount": amount,
            "amount_reversed": 0,
            "currency": "usd",
            "destination": destination,
            "created": self.seconds() if self.seconds else FIRST_CREATED + self._ids,
            "livemode": False,
            "reversed": False,
            "metadata": metadata,
            "transfer_group": group,
            "balance_transaction": f"txn_fake{self._ids:04d}",
        }
        self.transfers.append(transfer)
        return transfer

    def _list_transfers(self, form: dict[str, str]) -> dict[str, Any]:
        if "transfer_group" in form:
            group = form["transfer_group"]
            sent = [t for t in reversed(self.transfers) if t["transfer_group"] == group]
            return {"object": "list", "url": "/v1/transfers", "has_more": False, "data": sent}
        since = int(form.get("created[gte]", "0"))
        newest_first = [t for t in reversed(self.transfers) if t["created"] >= since]
        after = form.get("starting_after")
        if after is not None:
            ids = [t["id"] for t in newest_first]
            newest_first = newest_first[ids.index(after) + 1 :] if after in ids else []
        limit = int(form.get("limit", "10"))
        page = newest_first[:limit]
        return {"object": "list", "url": "/v1/transfers", "has_more": len(newest_first) > limit, "data": page}

    def _retrieve_transfer(self, transfer_id: str, form: dict[str, str]) -> Response:
        found = next((t for t in self.transfers if t["id"] == transfer_id), None)
        if found is None:
            message = f"No such transfer: '{transfer_id}'"
            return 404, {"error": {"type": "invalid_request_error", "code": "resource_missing", "message": message}}
        if "balance_transaction" not in form.values():
            return 200, found
        movement = {
            "id": found["balance_transaction"],
            "object": "balance_transaction",
            "amount": -found["amount"],
            "fee": 0,
            "net": -found["amount"],
            "status": "available",
            "available_on": found["created"],
            "currency": "usd",
        }
        return 200, {**found, "balance_transaction": movement}

    def _new_id(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}_fake{self._ids:04d}"
