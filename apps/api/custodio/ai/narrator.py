"""Plain-language actas. The model rewrites; code checks that every number it wrote is in the decision."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from custodio import llm
from custodio.ai.numbers import amounts_in
from custodio.ai.views import as_json
from custodio.config import get_settings
from custodio.contracts import Decision, Model

_MAX_CHARS = 900


class Narration(Model):
    text: str


SYSTEM = """\
You explain one payment decision of Custodio, an accounts-payable agent, to a person with no finance background \
(a shop owner, a new assistant). You receive the decision record ("acta") as JSON: the twelve rules with their \
outcomes and reasons, the verdict, the status, the engine's own explanation and what would have made it payable.

Write in neutral Latin American Spanish, 2 to 4 short sentences, no lists, no markdown, no jargon (say "una \
persona debe aprobarla", not "escalada"; "la cuenta no es la de siempre", not "R4 falló"). Say what happened, why, \
and what the reader can do next.

Numbers: copy every figure exactly as it appears in the acta, in digits, with its currency. Never compute a new \
number (no differences, sums, percentages or rounding) and never add a figure that is not in the acta. Code \
rejects the whole text if any number in it is not in the acta.

The decision is final and was taken by code: do not soften it, contradict it or suggest that the rules be bypassed.
"""


def narrate(decision: Decision) -> str:
    """Plain-language version of an acta. Every number in the output must appear in the decision."""
    try:
        narration = llm.structured(
            model=get_settings().model_fast,
            system=SYSTEM,
            content=f"<acta>\n{as_json(decision.model_dump(mode='json', exclude={'narrative'}))}\n</acta>",
            schema=Narration,
            effort="low",
            max_tokens=2000,
        ).value
    except llm.LLMError:
        return decision.explanation
    text = narration.text.strip()
    if not text or len(text) > _MAX_CHARS or not numbers_match(text, decision):
        return decision.explanation
    return text


def numbers_match(text: str, decision: Decision) -> bool:
    return amounts_in(text) <= _numbers_of(decision.model_dump(mode="json"))


def _numbers_of(value: Any) -> set[Decimal]:
    """Every number in the decision: numeric fields, and the figures written inside its texts and dates."""
    if isinstance(value, bool) or value is None:
        return set()
    if isinstance(value, int | float):
        return {Decimal(str(value)).normalize()}
    if isinstance(value, str):
        return amounts_in(value)
    if isinstance(value, dict):
        return set().union(*(_numbers_of(v) for v in value.values()))
    if isinstance(value, list):
        return {Decimal(len(value))}.union(*(_numbers_of(v) for v in value))
    return set()
