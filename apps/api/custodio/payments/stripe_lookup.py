"""Reading back from Stripe what the rail sent: the proof behind a `tr_…` id, asked live, never from Keeper's copy.

Read only. A lookup has a short timeout and no retries (a person is looking at the acta), answers are kept a few
seconds so a reload does not ask Stripe again, and any Stripe failure becomes `StripeUnavailableError` without
Stripe's own message (it can quote part of the key).
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

import stripe

TRANSFER_ID = re.compile(r"tr_[A-Za-z0-9]{1,64}")
RESOURCE_MISSING = "resource_missing"
PAGE_SIZE = 100
MAX_PAGES = 10  # 1.000 transfers: far above the 40 a workspace may send
LOOKUP_TIMEOUT_SECONDS = 6
CACHE_SECONDS = 10.0


class StripeUnavailableError(Exception):
    """Stripe could not be asked right now (network, key, rate limit or an unexpected answer)."""


@dataclass(frozen=True)
class BalanceMovement:
    """The platform balance transaction a transfer produced: what it took from the test balance and when."""

    id: str
    amount_cents: int
    fee_cents: int
    net_cents: int
    status: str
    available_on: datetime | None


@dataclass(frozen=True)
class StripeTransfer:
    id: str
    amount_cents: int
    currency: str
    destination: str | None
    created: datetime
    livemode: bool
    reversed: bool
    amount_reversed_cents: int
    transfer_group: str | None
    metadata: Mapping[str, str]
    balance: BalanceMovement | None
    fetched_at: datetime  # when Stripe answered, so the acta can say how fresh the proof is
    raw: dict[str, Any] = field(compare=False, repr=False)

    @property
    def workspace_id(self) -> str | None:
        return self.metadata.get("workspace_id")

    @property
    def invoice_id(self) -> str | None:
        return self.metadata.get("invoice_id")


@dataclass(frozen=True)
class TransferListing:
    transfers: tuple[StripeTransfer, ...]
    complete: bool  # False when Stripe had more than this reads; the cuadre then says so
    fetched_at: datetime


class StripeLookup(Protocol):
    def transfer(self, transfer_id: str) -> StripeTransfer | None:
        """None when Stripe has no such transfer."""
        ...

    def transfers_since(self, since: datetime) -> TransferListing: ...


class StripeApiLookup:
    def __init__(self, client: stripe.StripeClient) -> None:
        self._client = client

    @classmethod
    def with_key(cls, secret_key: str) -> StripeApiLookup:
        http = stripe.new_default_http_client(timeout=LOOKUP_TIMEOUT_SECONDS)
        return cls(stripe.StripeClient(secret_key, http_client=http, max_network_retries=0))

    def transfer(self, transfer_id: str) -> StripeTransfer | None:
        if not TRANSFER_ID.fullmatch(transfer_id):
            return None
        try:
            found = self._client.v1.transfers.retrieve(transfer_id, params={"expand": ["balance_transaction"]})
        except stripe.InvalidRequestError as error:
            if error.code == RESOURCE_MISSING:
                return None
            raise StripeUnavailableError() from None
        except stripe.StripeError:
            raise StripeUnavailableError() from None
        return _transfer_of(found, datetime.now(UTC))

    def transfers_since(self, since: datetime) -> TransferListing:
        transfers: list[StripeTransfer] = []
        after: str | None = None
        fetched_at = datetime.now(UTC)
        try:
            for _ in range(MAX_PAGES):
                page = self._client.v1.transfers.list(params=_page_params(since, after))
                transfers.extend(_transfer_of(item, fetched_at) for item in page.data)
                if not page.has_more or not page.data:
                    return TransferListing(tuple(transfers), complete=True, fetched_at=fetched_at)
                after = page.data[-1].id
        except stripe.StripeError:
            raise StripeUnavailableError() from None
        return TransferListing(tuple(transfers), complete=False, fetched_at=fetched_at)


class CachedLookup:
    """Keeps each answer a few seconds. Failures are never kept: the next look asks Stripe again."""

    def __init__(
        self, inner: StripeLookup, ttl_seconds: float = CACHE_SECONDS, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._inner = inner
        self._ttl = ttl_seconds
        self._clock = clock
        self._transfers: dict[str, tuple[float, StripeTransfer | None]] = {}
        self._listings: dict[datetime, tuple[float, TransferListing]] = {}

    def transfer(self, transfer_id: str) -> StripeTransfer | None:
        kept = self._transfers.get(transfer_id)
        if kept is not None and self._fresh(kept[0]):
            return kept[1]
        found = self._inner.transfer(transfer_id)
        self._transfers[transfer_id] = (self._clock(), found)
        return found

    def transfers_since(self, since: datetime) -> TransferListing:
        kept = self._listings.get(since)
        if kept is not None and self._fresh(kept[0]):
            return kept[1]
        listing = self._inner.transfers_since(since)
        self._listings[since] = (self._clock(), listing)
        return listing

    def _fresh(self, stored_at: float) -> bool:
        return self._clock() - stored_at < self._ttl


def _page_params(since: datetime, after: str | None) -> stripe.params.TransferListParams:
    params: stripe.params.TransferListParams = {"created": {"gte": int(since.timestamp())}, "limit": PAGE_SIZE}
    if after is not None:
        params["starting_after"] = after
    return params


def _transfer_of(transfer: stripe.Transfer, fetched_at: datetime) -> StripeTransfer:
    return StripeTransfer(
        id=transfer.id,
        amount_cents=transfer.amount,
        currency=transfer.currency,
        destination=_id_of(transfer.destination),
        created=datetime.fromtimestamp(transfer.created, UTC),
        livemode=transfer.livemode,
        reversed=transfer.reversed,
        amount_reversed_cents=transfer.amount_reversed,
        transfer_group=transfer.transfer_group,
        metadata=_metadata_of(transfer.to_dict().get("metadata")),
        balance=_balance_of(transfer.balance_transaction),
        fetched_at=fetched_at,
        raw=transfer.to_dict(),
    )


def _id_of(value: str | stripe.StripeObject | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    identifier = getattr(value, "id", None)
    return identifier if isinstance(identifier, str) else None


def _metadata_of(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _balance_of(value: str | stripe.BalanceTransaction | None) -> BalanceMovement | None:
    if not isinstance(value, stripe.BalanceTransaction):
        return None
    available_on = getattr(value, "available_on", None)
    return BalanceMovement(
        id=value.id,
        amount_cents=value.amount,
        fee_cents=value.fee,
        net_cents=value.net,
        status=value.status,
        available_on=datetime.fromtimestamp(available_on, UTC) if isinstance(available_on, int) else None,
    )
