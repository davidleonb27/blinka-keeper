"""Text addressed to an AI agent instead of to a person (R2).

An invoice talks to the company that pays it; it never talks to the agent. Any line that addresses an assistant,
claims a prior approval, asks to skip review or tries to change the rules is an instruction, and instructions in a
document are never obeyed. The patterns run over folded text (lowercase, no accents), in Spanish and English.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from custodio.engine.text import fold

_AGENT = r"(?:asistente|agente|modelo|bot|sistema)(?: de (?:ia|inteligencia artificial|pagos))?"
_AI = r"(?:ai|a\.i\.|llm|ia)"

INSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        # Addressing the machine.
        r"\b(?:asistente|agente|modelo) de (?:ia|inteligencia artificial)\b",
        rf"\b{_AI} (?:assistant|agent|model|system)\b",
        rf"\b(?:nota|mensaje|instrucciones?|aviso) (?:para|al|a la) (?:el |la )?{_AGENT}\b",
        rf"\b(?:note|message|instructions?) (?:to|for) (?:the )?(?:{_AI} )?(?:assistant|agent|model|bot|system)\b",
        r"\b(?:system prompt|prompt del sistema)\b",
        # Overriding instructions or rules.
        r"\bignor(?:a|e|en|ar|ad)\b.{0,30}\b(?:reglas|instrucciones|politicas?|rules|instructions|polic(?:y|ies)|previous|anteriores)\b",
        r"\b(?:olvida|olvide|forget|disregard)\b.{0,30}\b(?:reglas|instrucciones|rules|instructions|previous|anteriores)\b",
        r"\b(?:nuevas instrucciones|new instructions|override|bypass)\b",
        r"\b(?:sube|subir|aumenta|aumentar|eleva|elevar|cambia|cambiar|modifica|modificar|raise|increase|change)\b"
        r".{0,20}\b(?:limite|tope|cupo|reglas?|politica|limit|threshold|budget|rules?|policy)\b",
        # Claiming an approval that did not happen here.
        r"\bya (?:fue|esta|ha sido) (?:aprobad|autorizad)",
        r"\bpre-?(?:aprobad|autorizad|approved|authori[sz]ed)",
        r"\balready (?:been )?(?:approved|authori[sz]ed)\b",
        r"\bmarca(?:r|la)? (?:esta )?(?:factura )?como (?:aprobada|pagada|verificada)\b",
        r"\bmark (?:this|it) (?:invoice )?as (?:approved|paid|verified)\b",
        # Skipping review or forcing the payment.
        r"\bsin (?:revision|revisar|verificar|verificacion|validacion|validar|aprobacion)\b",
        r"\b(?:without|skip(?:ping)?|no need for)(?: the| any)? (?:review|approval|verification|checks?)\b",
        r"\bprocesala\b",
        r"\b(?:process|pay) (?:this|it)(?: invoice)? (?:now|immediately|right away|without)\b",
        r"\b(?:pagala|paguela|pagar) (?:ya|de inmediato|inmediatamente)\b",
    )
)


@dataclass(frozen=True)
class InstructionLine:
    number: int  # 1-based line number in the text that was searched
    text: str  # the line as written, without surrounding spaces


def find_instruction(text: str) -> InstructionLine | None:
    """The first line of `text` that addresses the agent; None when there is none."""
    for number, line in enumerate(text.splitlines(), start=1):
        folded = fold(line)
        if any(pattern.search(folded) for pattern in INSTRUCTION_PATTERNS):
            return InstructionLine(number=number, text=line.strip())
    return None
