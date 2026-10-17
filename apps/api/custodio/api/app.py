"""The FastAPI application. `create_app()` wires production; tests pass a runtime with doubles."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from starlette.routing import Route

from custodio import __version__
from custodio.api import errors, mcp_server
from custodio.api.body_limit import BodySizeLimit
from custodio.api.routes import (
    challenge,
    decisions,
    firewall,
    health,
    invoices,
    ledger,
    onboarding,
    policy,
    redteam,
    telegram,
    workspaces,
)
from custodio.config import get_settings
from custodio.services.context import Runtime, production_runtime

API_PREFIX = "/api/v1"
ROUTERS = (health, workspaces, onboarding, policy, invoices, decisions, ledger, redteam, challenge, firewall, telegram)


def create_app(runtime: Runtime | None = None) -> FastAPI:
    runtime = runtime or production_runtime(get_settings(), os.environ.get("TELEGRAM_BOT_TOKEN"))
    mcp = mcp_server.build(runtime)
    mcp_app = mcp.streamable_http_app(
        streamable_http_path=mcp_server.PATH,
        stateless_http=True,
        json_response=True,
        host="0.0.0.0",  # noqa: S104
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            yield

    app = FastAPI(
        title="Custodio API",
        version=__version__,
        summary="The model reads, code decides, a person authorizes.",
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.runtime = runtime
    app.include_router(_api_router())
    app.router.routes.append(Route(mcp_server.PATH, endpoint=mcp_server.Gateway(runtime, mcp_app)))
    errors.install(app)
    app.add_middleware(BodySizeLimit)
    return app


def _api_router() -> APIRouter:
    router = APIRouter(prefix=API_PREFIX)
    for module in ROUTERS:
        router.include_router(module.router)
    return router
