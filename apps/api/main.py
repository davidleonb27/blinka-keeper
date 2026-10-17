"""Vercel entrypoint (`main:app`). Vercel forwards the original path, so every route lives under /api/v1."""

from fastapi import FastAPI

from custodio import __version__
from custodio.api import router

app = FastAPI(
    title="Custodio API",
    version=__version__,
    summary="The model reads, code decides, a person authorizes.",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
)
app.include_router(router)
