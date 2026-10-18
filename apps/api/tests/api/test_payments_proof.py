"""«Pago en Stripe» in the acta, /pagos with the record ↔ Stripe match, and the pain.001 file for Blinka.

The rail and the lookup both talk to the fake Stripe transport under the real SDK, without cache, so each test
can change what Stripe says between two requests.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from custodio.api.app import create_app
from custodio.db import Database
from custodio.payments import STRIPE_TEST, RailChoice, StripeAccountTable, StripeApiLookup, StripeTestRail
from custodio.payments.port import Clock
from custodio.services.context import RateLimits, Runtime
from custodio.services.lanes import Lanes
from tests.payments.stripe_fake import FakeStripe

from .conftest import MutableClock
from .helpers import Workspace, new_workspace, process

SCHEMA = etree.XMLSchema(etree.parse(str(Path(__file__).parents[1] / "payments" / "schemas" / "pain.001.001.09.xsd")))
NS = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"}


@pytest.fixture
def stripe_http() -> FakeStripe:
    return FakeStripe()


def stripe_choice(fake: FakeStripe) -> RailChoice:
    client = fake.client()

    def build(session: Any, clock: Clock) -> StripeTestRail:
        return StripeTestRail(client, StripeAccountTable(session, clock), clock=clock)

    return RailChoice(name=STRIPE_TEST, build=build, lookup=StripeApiLookup(client))


@pytest.fixture
def runtime(
    database: Database, lanes: Lanes, clock: MutableClock, limits: RateLimits, stripe_http: FakeStripe
) -> Runtime:
    return Runtime(
        database=database,
        lanes=lanes,
        clock=clock,
        limits=limits,
        public_base_url="https://custodio.test",
        payment_rail=stripe_choice(stripe_http),
    )


def get(client: TestClient, workspace: Workspace, path: str, status: int = 200) -> dict[str, Any]:
    response = client.get(f"/api/v1{path}", headers=workspace.headers)
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    return body


def checks(proof: dict[str, Any]) -> dict[str, bool]:
    return {check["field"]: check["ok"] for check in proof["checks"]}


def sent_transfer(stripe_http: FakeStripe, workspace: Workspace, invoice_id: str) -> dict[str, Any]:
    return next(t for t in stripe_http.transfers if t["transfer_group"] == f"{workspace.id}:{invoice_id}")


@pytest.fixture
def paid_workspace(client: TestClient) -> Workspace:
    workspace = new_workspace(client)
    process(client, workspace)
    return workspace


def test_the_acta_s_transfer_is_read_live_from_stripe_and_every_field_matches(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    transfer = sent_transfer(stripe_http, paid_workspace, "F01")
    reads_before = len([r for r in stripe_http.requests if r.method == "get"])

    proof = get(client, paid_workspace, "/payments/F01/stripe")

    assert proof["status"] == "verified"
    assert checks(proof) == dict.fromkeys(
        ["amount", "currency", "beneficiary", "invoice", "livemode", "reversal"], True
    )
    assert proof["transfer"]["id"] == transfer["id"]
    assert proof["transfer"]["livemode"] is False
    assert proof["transfer"]["state"] == "paid"
    assert proof["transfer"]["balance_transaction"]["status"] == "available"
    assert proof["raw"]["id"] == transfer["id"]
    assert proof["dashboard_url"] == f"https://dashboard.stripe.com/test/connect/transfers/{transfer['id']}"
    assert len([r for r in stripe_http.requests if r.method == "get"]) == reads_before + 1


def test_a_transfer_that_differs_from_the_acta_is_flagged_field_by_field(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    transfer = sent_transfer(stripe_http, paid_workspace, "F01")
    transfer["amount"] += 1
    transfer["destination"] = "acct_somebody_else"

    proof = get(client, paid_workspace, "/payments/F01/stripe")

    assert proof["status"] == "mismatch"
    assert checks(proof) == {
        "amount": False,
        "currency": True,
        "beneficiary": False,
        "invoice": True,
        "livemode": True,
        "reversal": True,
    }


def test_a_transfer_stripe_does_not_have_is_said_plainly(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    stripe_http.transfers.remove(sent_transfer(stripe_http, paid_workspace, "F01"))

    proof = get(client, paid_workspace, "/payments/F01/stripe")

    assert proof["status"] == "missing"
    assert proof["raw"] is None
    assert "no tiene ninguna transferencia" in proof["message"]


def test_stripe_down_is_an_answer_not_an_error(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    stripe_http.unreachable = True

    proof = get(client, paid_workspace, "/payments/F01/stripe")
    overview = get(client, paid_workspace, "/payments")

    assert proof["status"] == "unavailable"
    assert proof["message"].startswith("No se pudo consultar Stripe ahora")
    assert overview["stripe"]["status"] == "unavailable"
    assert overview["stripe"]["recorded_total"] > 0
    assert overview["payments"]


def test_a_payment_that_did_not_go_through_stripe_has_nothing_to_look_up(
    client: TestClient, paid_workspace: Workspace
) -> None:
    proof = get(client, paid_workspace, "/payments/F02/stripe")  # approved, waiting for its day in the calendar

    assert proof["status"] == "not_applicable"


def test_another_workspace_cannot_read_a_payment_or_see_its_transfers(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    other = new_workspace(client)

    get(client, other, "/payments/F01/stripe", status=404)  # F01 is undecided there
    overview = get(client, other, "/payments")

    assert overview["payments"] == []
    assert overview["stripe"]["lines"] == []
    assert overview["stripe"]["stripe_total"] == 0


def test_a_transfer_whose_metadata_names_another_workspace_is_never_shown(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    sent_transfer(stripe_http, paid_workspace, "F01")["metadata"]["workspace_id"] = "someone-else"

    proof = get(client, paid_workspace, "/payments/F01/stripe")

    assert proof["status"] == "mismatch"
    assert proof["transfer"] is None
    assert proof["raw"] is None


def test_payments_lists_the_workspace_s_payments_and_the_record_balances_with_stripe(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    overview = get(client, paid_workspace, "/payments")

    match = overview["stripe"]
    executed = [p for p in overview["payments"] if p["execution"] and p["execution"]["status"] == "executed"]
    assert overview["rail"] == "stripe_test"
    assert match["status"] == "balanced"
    assert match["complete"] is True
    assert {line["kind"] for line in match["lines"]} == {"matched"}
    assert {line["transfer_id"] for line in match["lines"]} == {p["execution"]["external_id"] for p in executed}
    assert match["recorded_total"] == match["stripe_total"]
    assert match["difference"] == 0
    assert overview["exportable"] >= len(executed)


def test_the_match_shows_what_is_missing_on_each_side_with_totals(
    client: TestClient, paid_workspace: Workspace, stripe_http: FakeStripe
) -> None:
    gone = sent_transfer(stripe_http, paid_workspace, "F01")
    stripe_http.transfers.remove(gone)
    stray = stripe_http.add_transfer(4_200, {"workspace_id": paid_workspace.id, "invoice_id": "F77"})

    match = get(client, paid_workspace, "/payments")["stripe"]

    kinds = {line["transfer_id"]: line["kind"] for line in match["lines"]}
    assert match["status"] == "differences"
    assert kinds[gone["id"]] == "missing_in_stripe"
    assert kinds[stray["id"]] == "missing_in_registry"
    expected = (
        sum(int(t["amount"]) for t in stripe_http.transfers if t["metadata"].get("workspace_id") == paid_workspace.id)
        / 100
    )
    assert float(match["stripe_total"]) == expected
    assert float(match["difference"]) == pytest.approx(float(match["stripe_total"]) - float(match["recorded_total"]))


def test_the_file_for_blinka_holds_the_approved_payments_and_passes_the_official_schema(
    client: TestClient, paid_workspace: Workspace
) -> None:
    overview = get(client, paid_workspace, "/payments")

    response = client.get("/api/v1/payments/pain001.xml", headers=paid_workspace.headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert response.headers["content-disposition"].startswith('attachment; filename="CUSTODIO-')
    document = etree.fromstring(response.content)
    SCHEMA.assertValid(document)
    ids = document.xpath("//p:EndToEndId/text()", namespaces=NS)
    assert len(ids) == overview["exportable"]
    assert "F01" in ids
    total = sum(float(a) for a in document.xpath("//p:InstdAmt/text()", namespaces=NS))
    assert float(document.xpath("//p:GrpHdr/p:CtrlSum/text()", namespaces=NS)[0]) == pytest.approx(total)
    assert document.xpath("//p:GrpHdr/p:InitgPty/p:Nm/text()", namespaces=NS)  # the company pays


def test_without_approved_payments_there_is_no_file(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = client.get("/api/v1/payments/pain001.xml", headers=workspace.headers)

    assert response.status_code == 409
    assert response.json()["code"] == "nothing_to_export"


def test_live_lookups_are_rate_limited_per_workspace(
    database: Database, lanes: Lanes, clock: MutableClock, stripe_http: FakeStripe
) -> None:
    limits = replace(RateLimits(), stripe_lookups_per_minute_per_workspace=2)
    runtime = Runtime(database, lanes, clock, limits, "https://custodio.test", stripe_choice(stripe_http))
    with TestClient(create_app(runtime)) as client:
        workspace = new_workspace(client)
        process(client, workspace)
        statuses = [client.get("/api/v1/payments", headers=workspace.headers).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
