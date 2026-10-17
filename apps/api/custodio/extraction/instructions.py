"""Text addressed to an AI agent, visible or not. It never changes a decision: R2 sends the invoice to a person.

The patterns extend the prototype's (prototype/engine.js, INJECTION_RE) and run on folded text (lowercase, no
accents), so "procésala" and "PROCESALA" match alike. They target talk to a machine and attempts to skip review;
ordinary payment instructions to a person ("favor pagar antes del vencimiento") do not match.
"""

from __future__ import annotations

import re

from custodio.contracts import HiddenTextFinding, HiddenTextKind
from custodio.extraction.source import SourceText
from custodio.extraction.text import fold, squash

_PATTERNS = (
    # talking to a machine
    r"\b(asistente|agente|modelo|sistema) de (ia|inteligencia artificial)\b",
    r"\b(ai|llm) (assistant|agent|model|system)\b",
    r"\b(language model|modelo de lenguaje|system prompt|instrucciones del sistema)\b",
    r"\b(nuevas|new) (instrucciones|instructions)\b",
    r"\b(agente|robot|bot) (de pagos?|pagador|automatico)\b",
    r"\bautomated (payment )?(system|agent|processor|reader)\b",
    # overriding rules
    r"\bignor(a|e|en|ar)\s+(las|todas|tus|sus|cualquier|all|any|previous|prior|the|your|as)\b",
    r"\b(olvida (las|tus|todas)|disregard|forget (all|previous|your))\b",
    # claiming approval or skipping review
    r"\b(ya|ja) (fue|foi|esta) (aprobad|aprovad|autorizad)",
    r"\b(pre-?aprobad|pre-?approved|already approved)",
    r"\b(sin|sem) (revision|revisao|aprobacion|aprovacao|validacion|verificacion)\b",
    r"\bwithout (review|approval|verification|checking)\b",
    r"\bmarca(r|la)? (esta|la) factura como (aprobada|pagada)\b",
    r"\bmark (this|the) invoice as (approved|paid)\b",
    r"\b(aprueba|autoriza|approve|authorize)(la|lo)? (automaticamente|automatically)\b",
    r"\bprocesala\b",
    r"\bprocess (this|it) (now|immediately|without)\b",
)
_INSTRUCTION = re.compile("|".join(_PATTERNS))


def find_instructions(source: SourceText) -> list[HiddenTextFinding]:
    """One INSTRUCTION finding per line of `source` that speaks to the agent."""
    return [
        _finding(squash(line), page)
        for page, text in enumerate(source.pages, start=1)
        for line in text.splitlines()
        if speaks_to_agent(line)
    ]


def speaks_to_agent(text: str) -> bool:
    return _INSTRUCTION.search(fold(text)) is not None


def _finding(line: str, page: int) -> HiddenTextFinding:
    return HiddenTextFinding(
        kind=HiddenTextKind.INSTRUCTION,
        text=line,
        page=page,
        detail=f"El documento trae texto dirigido al agente en la página {page}. El agente no obedece texto de "
        "las facturas y le pide a una persona que la revise.",
    )
