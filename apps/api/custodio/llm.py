"""The only door to Claude. Every model call in Custodio goes through `structured()`.

Rules that hold for every call:
- The model returns data that matches a Pydantic schema (structured outputs). It never returns a decision
  that code executes as-is: callers validate and the engine decides.
- Stable instructions go in `system` and are cached; volatile content goes in the user turn.
- A refusal, a truncated answer or an invalid object raises; callers turn that into "NO MEDIDO" or an
  escalation, never into a guess.
- Spend is estimated per call and capped per UTC day (Settings.llm_daily_budget_usd).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal

import anthropic
from anthropic import omit
from anthropic.types.beta import (
    BetaContentBlockParam,
    BetaImageBlockParam,
    BetaRequestDocumentBlockParam,
    BetaTextBlockParam,
    BetaToolUnionParam,
)
from pydantic import BaseModel

from custodio.config import get_settings

Effort = Literal["low", "medium", "high", "xhigh", "max"]

# USD per million tokens (input, output). Cache reads are billed at ~0.1x input.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
# Server-side refusal fallback ("default" routing) is available on these models only.
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    """The model could not produce a usable answer. Callers must not guess a replacement."""


class LLMRefused(LLMError):
    pass


class LLMTruncated(LLMError):
    pass


class LLMBudgetExceeded(LLMError):
    pass


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    value: T
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: float


class _Budget:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._spent = 0.0

    def check(self) -> None:
        limit = get_settings().llm_daily_budget_usd
        with self._lock:
            self._roll()
            if self._spent >= limit:
                raise LLMBudgetExceeded(f"Límite diario de gasto en modelos alcanzado ({limit:.2f} USD).")

    def add(self, usd: float) -> None:
        with self._lock:
            self._roll()
            self._spent += usd

    def spent_today(self) -> float:
        with self._lock:
            self._roll()
            return self._spent

    def _roll(self) -> None:
        today = datetime.now(UTC).date().isoformat()
        if today != self._day:
            self._day, self._spent = today, 0.0


budget = _Budget()


@lru_cache
def client() -> anthropic.Anthropic:
    return anthropic.Anthropic(max_retries=2, timeout=120.0)


def _cost(model: str, usage: Any) -> float:
    price_in, price_out = _PRICES.get(model, (4.0, 20.0))
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    fresh = usage.input_tokens or 0
    return (fresh * price_in + cache_write * price_in * 1.25 + cache_read * price_in * 0.1) / 1e6 + (
        usage.output_tokens or 0
    ) * price_out / 1e6


def structured[T: BaseModel](
    *,
    model: str,
    system: str,
    content: str | list[BetaContentBlockParam],
    schema: type[T],
    effort: Effort = "medium",
    max_tokens: int = 16000,
    tools: list[BetaToolUnionParam] | None = None,
) -> LLMResult[T]:
    """Ask Claude for an object of type `schema`.

    `content` is the user turn: a string, or a list of content blocks (text, image, document). Put the
    document blocks before the instruction text. `tools` is for server tools only (e.g. web_fetch).
    """
    budget.check()
    use_fallback = model in _FALLBACK_MODELS
    response = client().beta.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": content}],
        output_format=schema,
        output_config={"effort": effort},
        tools=tools if tools else omit,
        betas=[_FALLBACK_BETA] if use_fallback else omit,
        fallbacks="default" if use_fallback else omit,
    )
    cost = _cost(model, response.usage)
    budget.add(cost)

    if response.stop_reason == "refusal":
        category = getattr(response.stop_details, "category", None) if response.stop_details else None
        raise LLMRefused(f"El modelo se negó a responder (categoría: {category}).")
    if response.stop_reason == "max_tokens":
        raise LLMTruncated("La respuesta del modelo se cortó por longitud.")
    parsed = response.parsed_output
    if parsed is None:
        raise LLMError("El modelo no devolvió un objeto válido para el esquema pedido.")
    return LLMResult(
        value=parsed,
        model=response.model,
        input_tokens=response.usage.input_tokens or 0,
        output_tokens=response.usage.output_tokens or 0,
        cache_read_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        cost_usd=cost,
    )


def pdf_block(data_b64: str) -> BetaRequestDocumentBlockParam:
    return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data_b64}}


def image_block(
    data_b64: str, media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
) -> BetaImageBlockParam:
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data_b64}}


def text_block(text: str) -> BetaTextBlockParam:
    return {"type": "text", "text": text}
