"""MCP server (streamable HTTP, stateless, JSON responses) at /api/v1/mcp.

Another agent connects with the workspace API key as a Bearer token. The tools call the same services as the HTTP
firewall, with the same rate limits, so an intent gets the same decision whichever door it comes through.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from custodio import __version__
from custodio.api.deps import bearer_token, client_ip
from custodio.contracts import Decision, IntentVerdict, PaymentIntent, Policy
from custodio.db.models import WorkspaceRow
from custodio.services import firewall_service, policy_service, rate_limits, records, workspace_service
from custodio.services.context import Runtime, ServiceContext
from custodio.services.errors import InvalidApiKey, ServiceError

PATH = "/api/v1/mcp"
# Served behind Vercel on the public domain and authenticated by API key, so Host-header pinning (meant for local
# servers reachable from a browser) is off.
TRANSPORT_SECURITY = TransportSecuritySettings(enable_dns_rebinding_protection=False)
INSTRUCTIONS = (
    "Custodio es un firewall de pagos. Antes de pagar una factura, envía la intención de pago con "
    "submit_payment_intent: Custodio la decide con las reglas de la empresa y responde pagar, retener o escalar a una "
    "persona, con el acta y el hash en su registro. Nunca pagues algo que Custodio retuvo o escaló."
)


def build(runtime: Runtime) -> MCPServer:
    server = MCPServer(name="custodio", version=__version__, instructions=INSTRUCTIONS)

    @server.tool(description="Envía una intención de pago y recibe la decisión de Custodio con su acta.")
    def submit_payment_intent(intent: PaymentIntent, ctx: Context) -> IntentVerdict:
        request = _http_request(ctx)
        with _workspace(runtime, request) as (services, workspace):
            rate_limits.check_model_call(runtime, ip=client_ip(request), workspace_id=workspace.id)
            return firewall_service.submit(services, workspace, intent)

    @server.tool(description="Lee el acta de una decisión de este espacio por el id de la factura.")
    def get_decision(invoice_id: str, ctx: Context) -> Decision:
        with _workspace(runtime, _http_request(ctx)) as (services, workspace):
            return records.decision(services, workspace.id, invoice_id)

    @server.tool(description="Lee la política vigente: topes, reserva, monedas y beneficiarios permitidos.")
    def get_policy(ctx: Context) -> Policy:
        with _workspace(runtime, _http_request(ctx)) as (services, workspace):
            return policy_service.current(services, workspace.id)

    return server


class Gateway:
    """Refuses calls without a valid API key before they reach the MCP session machinery.

    A class, not a function, so Starlette mounts it as an ASGI app that accepts every method MCP uses.
    """

    def __init__(self, runtime: Runtime, app: ASGIApp) -> None:
        self.runtime = runtime
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not _authorized(self.runtime, Request(scope)):
            error = InvalidApiKey()
            body = json.dumps({"detail": error.message, "code": error.code}, ensure_ascii=False).encode()
            headers = [(b"content-type", b"application/json")]
            await send({"type": "http.response.start", "status": 401, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def _authorized(runtime: Runtime, request: Request) -> bool:
    runtime.database.ensure_migrated()
    with runtime.database.session() as session:
        try:
            _caller(runtime.context(session), request)
        except ServiceError:
            return False
    return True


@contextmanager
def _workspace(runtime: Runtime, request: Request) -> Iterator[tuple[ServiceContext, WorkspaceRow]]:
    """One unit of work for a tool call; service errors reach the calling agent as tool errors in Spanish."""
    with runtime.database.session() as session:
        services = runtime.context(session)
        try:
            yield services, _caller(services, request)
        except ServiceError as error:
            raise ToolError(error.message) from error


def _caller(services: ServiceContext, request: Request) -> WorkspaceRow:
    return workspace_service.by_api_key(services, bearer_token(request.headers.get("authorization")))


def _http_request(ctx: Context) -> Request:
    request = ctx.request_context.request
    if not isinstance(request, Request):
        raise ToolError(InvalidApiKey.message)
    return request
