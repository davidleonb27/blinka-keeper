from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from custodio import __version__
from custodio.config import get_settings

router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: str
    version: str
    anthropic: bool


@router.get("/health", response_model=Health)
def health() -> Health:
    settings = get_settings()
    return Health(
        status="ok",
        version=__version__,
        anthropic=settings.anthropic_configured,
    )
