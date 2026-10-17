from dataclasses import dataclass, field
from typing import Any

from custodio.extraction.ocr import Transcript
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
    """Stands in for custodio.llm.structured and remembers every call."""

    reading: InvoiceReading | None = None
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **kwargs: Any) -> LLMResult[InvoiceReading]:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.reading is not None
        return LLMResult(
            value=self.reading,
            model="claude-sonnet-5-5",
            input_tokens=1000,
            output_tokens=300,
            cache_read_tokens=0,
            cost_usd=0.005,
        )

    @property
    def sent_text(self) -> str:
        content = self.calls[-1]["content"]
        return content if isinstance(content, str) else " ".join(block["text"] for block in content)


@dataclass
class FakeGemini:
    """Stands in for custodio.extraction.ocr.transcribe."""

    text: str
    images: list[tuple[bytes, str]] = field(default_factory=list)

    def __call__(self, image: bytes, media_type: str) -> Transcript:
        self.images.append((image, media_type))
        return Transcript(text=self.text, model="gemini-test-flash")
