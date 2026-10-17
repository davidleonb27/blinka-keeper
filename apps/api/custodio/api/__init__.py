"""HTTP surface under /api/v1. Owned by lane L4; the health route is part of the base."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from custodio import __version__
from custodio.config import get_settings

router = APIRouter(prefix="/api/v1")


class Health(BaseModel):
    status: str
    version: str
    anthropic: bool
    gemini: bool


@router.get("/health", response_model=Health, tags=["system"])
def health() -> Health:
    settings = get_settings()
    return Health(
        status="ok",
        version=__version__,
        anthropic=settings.anthropic_configured,
        gemini=settings.gemini_configured,
    )
