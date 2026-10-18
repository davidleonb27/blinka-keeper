from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from custodio import __version__
from custodio.config import get_settings
from custodio.engine.sanctions import bundled_sanctions
from custodio.extraction import gemini, second_reading
from custodio.payments import RailName
from custodio.services.context import Runtime

router = APIRouter(tags=["system"])


class Health(BaseModel):
    status: str
    version: str
    anthropic: bool
    payment_rail: RailName
    sanctions_list_date: date | None = None  # publication date of the OFAC SDN copy R14 screens against


class GeminiHealth(BaseModel):
    configured: bool
    model: str
    status: str  # "ok", "sin configurar" or Google's reason codes for refusing the key


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    runtime: Runtime = request.app.state.runtime
    settings = get_settings()
    return Health(
        status="ok",
        version=__version__,
        anthropic=settings.anthropic_configured,
        payment_rail=runtime.payment_rail.name,
        sanctions_list_date=bundled_sanctions().published_on,
    )


@router.get("/health/gemini", response_model=GeminiHealth)
def gemini_health(leer: bool = False) -> GeminiHealth:
    """Why the second reader is or is not Gemini, without exposing the key. With `leer`, Gemini reads a one-line
    invoice exactly as a second reading does (a fraction of a cent, under the daily budget) and the status says
    whether that reading came back usable."""
    settings = get_settings()
    if not settings.gemini_configured:
        return GeminiHealth(configured=False, model=settings.gemini_model, status="sin configurar")
    status = gemini.probe(settings.gemini_model)
    if status == "ok" and leer:
        status = second_reading.gemini_check()
        if "404" in status:
            status = f"{status} Modelos Gemini disponibles: {', '.join(gemini.flash_models()) or 'ninguno'}"
    return GeminiHealth(configured=True, model=settings.gemini_model, status=status)
