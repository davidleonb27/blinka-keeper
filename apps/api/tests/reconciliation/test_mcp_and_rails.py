"""Other agents reconcile through MCP, and a Stripe transfer id in the statement is an exact reference."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.services.context import Runtime
from custodio.services.lanes import Lanes
from tests.api import doubles
from tests.api.conftest import MutableClock
from tests.api.helpers import new_workspace, process
from tests.api.test_mcp import call_tool, rpc
from tests.api.test_payments_stripe import stripe_choice
from tests.payments.stripe_fake import FakeStripe

from .conftest import GENEROUS


def test_the_mcp_server_offers_reconcile_statement(client: TestClient) -> None:
    workspace = new_workspace(client)

    tools = {tool["name"] for tool in rpc(client, workspace, "tools/list", {}).json()["result"]["tools"]}

    assert "reconcile_statement" in tools


def test_reconcile_statement_reconciles_the_demo_or_a_csv_for_the_callers_workspace(client: TestClient) -> None:
    workspace = new_workspace(client)
    process(client, workspace)

    demo = call_tool(client, workspace, "reconcile_statement", {"use_demo": True})
    csv = call_tool(
        client,
        workspace,
        "reconcile_statement",
        {"statement_csv": "Fecha;Descripción;Monto\n16/10/2026;PAGO PS-88412 PULSO SOFTWARE;-840,00\n"},
    )
    nothing = call_tool(client, workspace, "reconcile_statement", {})

    assert demo["isError"] is False
    assert demo["structuredContent"]["summary"]["reconciled"]["count"] == 17
    assert csv["structuredContent"]["movements"][0]["result"]["invoice_id"] == "F-005"
    assert nothing["isError"] is True


class TestStripeTransfers:
    @pytest.fixture
    def stripe_http(self) -> FakeStripe:
        return FakeStripe()

    @pytest.fixture
    def lanes(self) -> Lanes:
        return doubles.fake_lanes()

    @pytest.fixture
    def runtime(self, runtime: Runtime, stripe_http: FakeStripe) -> Runtime:
        return Runtime(
            database=runtime.database,
            lanes=runtime.lanes,
            clock=runtime.clock,
            limits=GENEROUS,
            public_base_url=runtime.public_base_url,
            payment_rail=stripe_choice(stripe_http),
        )

    def test_the_transfer_id_matches_the_payment_exactly(
        self, client: TestClient, stripe_http: FakeStripe, clock: MutableClock
    ) -> None:
        workspace = new_workspace(client)
        process(client, workspace)
        transfer: dict[str, Any] = stripe_http.transfers[0]
        statement = f"Fecha;Descripción;Referencia;Monto\n17/10/2026;WIRE OUT;{transfer['id']};-1.200,00\n"

        response = client.post(
            "/api/v1/reconciliations",
            headers=workspace.headers,
            files={"file": ("extracto.csv", statement.encode(), "text/csv")},
        )

        assert response.status_code == 201, response.text
        (item,) = response.json()["movements"]
        assert (item["result"]["level"], item["result"]["invoice_id"]) == ("exact", "F01")
        assert item["external_id"] == transfer["id"]
        assert item["dashboard_url"].endswith(transfer["id"])
        assert transfer["id"] in item["result"]["reason"]
