from dataclasses import dataclass, field
from typing import Any

from custodio.extraction.vision import Transcription

from custodio.extraction.structure import InvoiceReading, QuotedValue
from custodio.llm import LLMResult

GOOD_QUOTES: dict[str, tuple[str | None, str | None]] = {
    "supplier_name": ("Nube Andina S.A.S.", "Nube Andina S.A.S."),
    "supplier_tax_id": ("900.123.456-7", "NIT 900.123.456-7"),
    "invoice_number": ("FE-2041", "FE-2041"),
    "issue_date": ("2026-10-05", "Fecha de emisión: 05/10/2026"),
    "due_date": ("2026-10-20", "Fecha de vencimiento: 20/10/2026"),
    "amount": ("4200000.00", "COP 4.200.000,00"),
    "currency": ("COP", "COP 4.200.000,00"),
    "bank_name": ("Bancolombia", "Banco: Bancolombia"),
    "account_number": ("123-456789-01", "Cuenta No. 123-456789-01"),
    "description": ("Servicio de nube y respaldo, octubre 2026", "Servicio de nube y respaldo, octubre 2026"),
}


def make_reading(confidence: float = 0.95, **overrides: tuple[str | None, str | None]) -> InvoiceReading:
    quotes = GOOD_QUOTES | overrides
    return InvoiceReading(
        **{
            name: QuotedValue(value=value, quote=quote, confidence=confidence)
            for name, (value, quote) in quotes.items()
        }
    )


@dataclass
class FakeClaude:
    """Stands in for custodio.llm.structured and remembers every call.

    It answers a transcription request (vision) with `transcription` and a field request with `reading`.
    """

    reading: InvoiceReading | None = None
    transcription: str | None = None
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **kwargs: Any) -> LLMResult[Any]:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        value = Transcription(text=self.transcription or "") if kwargs["schema"] is Transcription else self.reading
        assert value is not None
        return LLMResult(
            value=value,
            model="claude-sonnet-5-5",
            input_tokens=1000,
            output_tokens=300,
            cache_read_tokens=0,
            cost_usd=0.005,
        )

    @property
    def sent_text(self) -> str:
        """Every text block sent to the model, across all calls."""
        return " ".join(
            block.get("text", "") for call in self.calls for block in call["content"] if isinstance(block, dict)
        )

    def blocks(self, kind: str) -> list[dict[str, Any]]:
        return [block for call in self.calls for block in call["content"] if block.get("type") == kind]
