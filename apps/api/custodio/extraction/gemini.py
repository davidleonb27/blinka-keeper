"""Gemini, only as the second reader of an invoice (`second_reading`), over its REST API.

The key is read from GEMINI_API_KEY and travels only in a request header; it never appears in an error. Spend goes
into the same daily budget as Claude's (`llm.budget`), so a day without budget stops both readers. Any failure
raises `GeminiError` (an `llm.LLMError`): the caller escalates, it never guesses.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Sequence

import httpx

from custodio import llm

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}"
MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SECONDS = 60.0
MAX_OUTPUT_TOKENS = 4096
# Gemini 2.5 thinks by default and its thoughts count against MAX_OUTPUT_TOKENS: an unbounded budget can end the
# answer with MAX_TOKENS, and every reading would become `unavailable`.
THINKING_BUDGET = 1024
# USD per million tokens (input, output), Gemini Flash list price; thinking tokens are billed as output.
PRICE_PER_MILLION = (0.30, 2.50)
_QUOTED_VALUE = {
    "type": "OBJECT",
    "properties": {
        "value": {"type": "STRING", "nullable": True},
        "quote": {"type": "STRING", "nullable": True},
        "confidence": {"type": "NUMBER"},
    },
    "required": ["value", "quote", "confidence"],
}


class GeminiError(llm.LLMError):
    """Gemini did not return a usable answer."""


def quoted_fields_schema(names: Sequence[str]) -> dict[str, object]:
    """A response schema with one value + quote + confidence object per field name."""
    return {"type": "OBJECT", "properties": dict.fromkeys(names, _QUOTED_VALUE), "required": list(names)}


def generate_json(
    *, model: str, system: str, text: str, images: Sequence[tuple[bytes, str]], schema: dict[str, object]
) -> object:
    """Ask Gemini for a JSON object matching `schema`; images go before the text."""
    llm.budget.check()
    parts = [{"inlineData": {"mimeType": media, "data": base64.b64encode(data).decode()}} for data, media in images]
    body: dict[str, object] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
            "temperature": 0,
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "thinkingConfig": {"thinkingBudget": THINKING_BUDGET},
        },
    }
    payload = _post(model, body)
    llm.budget.add(_cost(payload))
    return _answer(payload)


def _post(model: str, body: dict[str, object]) -> dict[str, object]:
    headers = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}
    try:
        response = httpx.post(ENDPOINT.format(model=model), json=body, headers=headers, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        raise GeminiError(f"Gemini no respondió ({type(error).__name__}).") from None
    if response.status_code != httpx.codes.OK:
        raise GeminiError(f"Gemini respondió con estado {response.status_code}{_reason(response)}.")
    payload = response.json()
    if not isinstance(payload, dict):
        raise GeminiError("Gemini devolvió una respuesta que no es un objeto.")
    return payload


def _answer(payload: dict[str, object]) -> object:
    try:
        candidate = payload["candidates"][0]  # type: ignore[index]
        reason = candidate.get("finishReason")
        if reason != "STOP":
            raise GeminiError(f"Gemini no terminó la respuesta (motivo: {reason}).")
        return json.loads(candidate["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise GeminiError("Gemini devolvió una respuesta sin un objeto válido.") from error


def _cost(payload: dict[str, object]) -> float:
    usage = payload.get("usageMetadata")
    if not isinstance(usage, dict):
        return 0.0
    tokens_in = usage.get("promptTokenCount", 0)
    tokens_out = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
    price_in, price_out = PRICE_PER_MILLION
    return float(tokens_in * price_in + tokens_out * price_out) / 1e6


def probe(model: str) -> str:
    """Whether the configured key may use `model`, asked without generating anything (so it costs nothing).

    Returns "ok" or the reason Google gives (its status and reason codes only, never the key)."""
    headers = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}
    try:
        response = httpx.get(MODEL_URL.format(model=model), headers=headers, timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as error:
        return f"sin respuesta ({type(error).__name__})"
    if response.status_code == httpx.codes.OK:
        return "ok"
    return f"estado {response.status_code}{_reason(response)}"


def generating_models() -> list[str]:
    """The Gemini models this key may call generateContent on, so a 404 says which name to use instead."""
    headers = {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}
    try:
        response = httpx.get(MODELS_URL, headers=headers, timeout=TIMEOUT_SECONDS, params={"pageSize": 1000})
        models = response.json().get("models", []) if response.status_code == httpx.codes.OK else []
    except (httpx.HTTPError, ValueError):
        return []
    return sorted(
        str(model["name"]).removeprefix("models/")
        for model in models
        if isinstance(model, dict)
        and "gemini" in str(model.get("name", ""))
        and "generateContent" in (model.get("supportedGenerationMethods") or [])
    )


def _reason(response: httpx.Response) -> str:
    """Google's machine-readable cause (e.g. PERMISSION_DENIED · SERVICE_DISABLED); free text is left out."""
    try:
        error = response.json().get("error", {})
    except ValueError:
        return ""
    if not isinstance(error, dict):
        return ""
    codes = [str(error.get("status") or "")]
    for detail in error.get("details") or []:
        if isinstance(detail, dict) and detail.get("reason"):
            codes.append(str(detail["reason"]))
    codes = [code for code in codes if code.replace("_", "").isalnum()]
    return f" ({' · '.join(codes)})" if codes else ""
