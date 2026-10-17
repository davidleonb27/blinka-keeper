from typing import Any

from fastapi.testclient import TestClient

from .helpers import Workspace, new_workspace, process
from .test_firewall import intent

MCP = "/api/v1/mcp"
STREAMABLE = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


def rpc(client: TestClient, workspace: Workspace | None, method: str, params: dict[str, Any]) -> Any:
    headers = {**STREAMABLE, **(workspace.bearer if workspace else {})}
    return client.post(MCP, headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})


def call_tool(client: TestClient, workspace: Workspace, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = rpc(client, workspace, "tools/call", {"name": name, "arguments": arguments})
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()["result"]
    return result


def test_the_server_offers_the_three_tools(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = rpc(client, workspace, "tools/list", {})

    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert names == {"submit_payment_intent", "get_decision", "get_policy"}


def test_the_server_refuses_calls_without_an_api_key(client: TestClient) -> None:
    response = rpc(client, None, "tools/list", {})

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_api_key"


def test_submit_payment_intent_answers_the_firewall_verdict(client: TestClient) -> None:
    workspace = new_workspace(client)

    result = call_tool(client, workspace, "submit_payment_intent", {"intent": intent()})

    assert result["isError"] is False
    assert result["structuredContent"]["decision"]["status"] == "paid_auto"
    assert result["structuredContent"]["ledger_hash"]


def test_get_decision_reads_only_the_callers_workspace(client: TestClient) -> None:
    owner, other = new_workspace(client), new_workspace(client, mode="blank")
    process(client, owner)

    mine = call_tool(client, owner, "get_decision", {"invoice_id": "F03"})
    theirs = call_tool(client, other, "get_decision", {"invoice_id": "F03"})

    assert mine["structuredContent"]["status"] == "hold"
    assert theirs["isError"] is True
    assert "No encontramos" in theirs["content"][0]["text"]


def test_get_policy_returns_the_current_policy(client: TestClient) -> None:
    workspace = new_workspace(client)

    result = call_tool(client, workspace, "get_policy", {})

    assert result["structuredContent"]["version"] == 1
    assert result["structuredContent"]["approval_threshold"] == 5000.0
