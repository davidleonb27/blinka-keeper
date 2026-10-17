"""The FastAPI application. `create_app()` wires production; tests pass a runtime with doubles."""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI

from custodio import __version__
from custodio.api import errors
from custodio.api.body_limit import BodySizeLimit
from custodio.api.routes import decisions, health, invoices, ledger, policy, workspaces
from custodio.config import get_settings
from custodio.services.context import Runtime, production_runtime

API_PREFIX = "/api/v1"


def create_app(runtime: Runtime | None = None) -> FastAPI:
    app = FastAPI(
        title="Custodio API",
        version=__version__,
        summary="The model reads, code decides, a person authorizes.",
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        redoc_url=None,
    )
    app.state.runtime = runtime or production_runtime(get_settings(), os.environ.get("TELEGRAM_BOT_TOKEN"))
    app.include_router(_api_router())
    errors.install(app)
    app.add_middleware(BodySizeLimit)
    return app


def _api_router() -> APIRouter:
    router = APIRouter(prefix=API_PREFIX)
    for module in (health, workspaces, policy, invoices, decisions, ledger):
        router.include_router(module.router)
    return router
