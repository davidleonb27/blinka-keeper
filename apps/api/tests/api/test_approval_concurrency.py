"""Two people approving with an updated agreement at once: the one that loses never moves money.

The other approval's new version lands between this one's check and its claim (as a concurrent request would commit
it); the rail must not be called for an approval whose agreement can no longer be written.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.db import Database
from custodio.payments import SIMULATED, RailChoice
from custodio.services import approval_service, policy_service, records
from custodio.services.context import RateLimits, Runtime, ServiceContext
from custodio.services.lanes import Lanes

from .conftest import MutableClock
from .doubles import model_free_lanes
from .helpers import new_workspace
from .test_approval_learning import ANA, REASON, pending_nube, policy
from .test_payments_surfaces import RecordingRail


@pytest.fixture
def lanes() -> Lanes:
    return model_free_lanes()


@pytest.fixture
def rail(clock: MutableClock) -> RecordingRail:
    return RecordingRail(clock)


@pytest.fixture
def runtime(database: Database, lanes: Lanes, clock: MutableClock, limits: RateLimits, rail: RecordingRail) -> Runtime:
    return Runtime(
        database=database,
        lanes=lanes,
        clock=clock,
        limits=limits,
        public_base_url="https://custodio.test",
        payment_rail=RailChoice(name=SIMULATED, build=lambda _session, _clock: rail),
    )


def a_rival_version_lands_while_claiming(monkeypatch: pytest.MonkeyPatch) -> None:
    claim: Callable[..., bool] = records.claim_pending

    def claim_after_a_rival(ctx: ServiceContext, workspace_id: str, invoice_id: str) -> bool:
        current = policy_service.current(ctx, workspace_id)
        policy_service.apply(ctx, workspace_id, current.model_copy(update={"reserve": current.reserve + 1}))
        return claim(ctx, workspace_id, invoice_id)

    monkeypatch.setattr(approval_service.records, "claim_pending", claim_after_a_rival)


def test_an_approval_whose_agreement_lost_the_race_never_pays(
    client: TestClient, rail: RecordingRail, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = new_workspace(client)
    invoice_id = pending_nube(client, workspace)
    paid_before = list(rail.orders)
    a_rival_version_lands_while_claiming(monkeypatch)

    body: dict[str, Any] = {"approver": ANA, "reason": REASON, "amount": "2236.00", "expected_policy_version": 1}
    response = client.post(f"/api/v1/decisions/{invoice_id}/approve-with-agreement", headers=workspace.headers, json=body)

    assert response.status_code == 409, response.text
    assert response.json()["code"] == "policy_changed"
    assert rail.orders == paid_before  # the rail was never called for it
    monkeypatch.undo()
    assert policy(client, workspace)["version"] == 1
    decision = client.get(f"/api/v1/decisions/{invoice_id}", headers=workspace.headers).json()["decision"]
    assert decision["status"] == "pending_approval"

