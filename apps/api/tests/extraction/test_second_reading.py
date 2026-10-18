"""The second, independent reading: it runs beside the first, is compared field by field and fails closed."""

from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from custodio import llm
from custodio.config import get_settings
from custodio.contracts import CrossCheckStatus, InvoiceSource, ReadingCrossCheck
from custodio.extraction import cross_check, extract_document, extract_text, render_invoice, second_reading
from custodio.extraction.second_reading import CriticalReading
from custodio.extraction.structure import QuotedValue
from custodio.extraction.vision import Transcription
from tests.extraction.doubles import GOOD_QUOTES, make_reading
from tests.extraction.factories import make_spec

REAL_START = cross_check.start
TEXT = render_invoice(make_spec(channel=InvoiceSource.TEXT)).data.decode()
SECOND_MODEL = "claude-opus-5-5"


def second(**overrides: str | None) -> CriticalReading:
    """What the second reader answers: the good values unless overridden."""
    values = {name: GOOD_QUOTES[name] for name in second_reading.COMPARED}
    return CriticalReading(
        **{
            name: QuotedValue(value=overrides.get(name, value), quote=quote, confidence=0.9)
            for name, (value, quote) in values.items()
        }
    )


@dataclass
class TwoReaders:
    """Stands in for llm.structured: the first reader (and vision) as before, the second by its own schema."""

    answer: CriticalReading = field(default_factory=second)
    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, **kwargs: Any) -> llm.LLMResult[Any]:
        self.calls.append(kwargs)
        schema = kwargs["schema"]
        if schema is CriticalReading and self.error is not None:
            raise self.error
        value: Any = {CriticalReading: self.answer, Transcription: Transcription(text=TEXT)}.get(schema, make_reading())
        return llm.LLMResult(
            value=value, model=kwargs["model"], input_tokens=1, output_tokens=1, cache_read_tokens=0, cost_usd=0.0
        )

    def second_calls(self) -> list[dict[str, Any]]:
        return [call for call in self.calls if call["schema"] is CriticalReading]


@pytest.fixture
def readers(monkeypatch: pytest.MonkeyPatch) -> TwoReaders:
    fake = TwoReaders()
    monkeypatch.setattr(llm, "structured", fake)
    monkeypatch.setattr(cross_check, "start", REAL_START)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return fake


def read_text(text: str = TEXT) -> ReadingCrossCheck:
    checked = extract_text(text, document_id="doc").cross_check
    assert checked is not None
    return checked


def field_check(checked: ReadingCrossCheck, name: str) -> Any:
    return next(comparison for comparison in checked.fields if comparison.field == name)


def test_two_readers_that_agree_on_the_four_fields(readers: TwoReaders) -> None:
    checked = read_text()
    assert checked.status is CrossCheckStatus.AGREE
    assert [f.field for f in checked.fields] == ["supplier_name", "amount", "currency", "account_number"]
    assert all(f.agree for f in checked.fields)
    [call] = readers.second_calls()
    assert call["model"] == SECOND_MODEL and call["system"] == second_reading.SYSTEM_PROMPT


def test_the_second_reader_uses_another_model_and_another_prompt(readers: TwoReaders) -> None:
    read_text()
    first = next(call for call in readers.calls if call["schema"] is not CriticalReading)
    [other] = readers.second_calls()
    assert first["model"] != other["model"] and first["system"] != other["system"]


def test_without_gemini_the_code_reader_votes_on_a_document_with_text(readers: TwoReaders) -> None:
    amount = field_check(read_text(), "amount")
    assert [reading.reader for reading in amount.readings] == ["claude-sonnet-5-5", SECOND_MODEL, "etiquetas"]


def test_every_reading_keeps_its_quote(readers: TwoReaders) -> None:
    account = field_check(read_text(), "account_number")
    assert all(reading.quote for reading in account.readings)


@pytest.mark.parametrize(
    ("name", "other"),
    [
        ("supplier_name", "Nube Andina Dos S.A.S."),
        ("amount", "42000000.00"),
        ("currency", "USD"),
        ("account_number", "123-456789-02"),
    ],
)
def test_a_disagreement_on_any_compared_field_is_reported(readers: TwoReaders, name: str, other: str) -> None:
    readers.answer = second(**{name: other})
    checked = read_text()
    assert checked.status is CrossCheckStatus.DISAGREE
    assert [f.field for f in checked.fields if not f.agree] == [name]


def test_a_field_the_second_reader_would_not_read_is_a_disagreement(readers: TwoReaders) -> None:
    readers.answer = second(amount=None)
    checked = read_text()
    assert checked.status is CrossCheckStatus.DISAGREE and not field_check(checked, "amount").agree


@pytest.mark.parametrize(
    ("name", "written"),
    [
        ("amount", "4.200.000,00"),
        ("amount", "4,200,000.00"),
        ("amount", "4200000"),
        ("supplier_name", "NUBE ANDINA SAS"),
        ("supplier_name", "nube  andina s.a.s."),
        ("currency", "cop"),
        ("account_number", "123 456789 01"),
        ("account_number", "12345678901"),
    ],
)
def test_the_same_value_written_another_way_agrees(readers: TwoReaders, name: str, written: str) -> None:
    readers.answer = second(**{name: written})
    assert read_text().status is CrossCheckStatus.AGREE


@pytest.mark.parametrize(
    ("error", "why"),
    [
        (llm.LLMError("se cayó"), "falló"),
        (llm.LLMRefused("no"), "falló"),
        (llm.LLMBudgetExceeded("tope"), "presupuesto"),
        (RuntimeError("inesperado"), "falló"),
    ],
)
def test_a_second_reader_that_fails_is_unavailable_never_skipped(
    readers: TwoReaders, error: Exception, why: str
) -> None:
    readers.error = error
    checked = read_text()
    assert checked.status is CrossCheckStatus.UNAVAILABLE and checked.fields == []
    assert checked.error is not None and why in checked.error


def test_a_second_reader_that_does_not_answer_in_time_is_unavailable(
    readers: TwoReaders, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CUSTODIO_SECOND_READING_TIMEOUT_SECONDS", "0.01")
    get_settings.cache_clear()
    monkeypatch.setattr(second_reading, "read", lambda document: __import__("time").sleep(0.5))
    try:
        checked = read_text()
    finally:
        get_settings.cache_clear()
    assert checked.status is CrossCheckStatus.UNAVAILABLE and "a tiempo" in (checked.error or "")


def test_an_exhausted_daily_budget_stops_the_second_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cross_check, "start", REAL_START)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-for-doubles")
    monkeypatch.setattr(llm.budget, "check", _raise_budget)
    monkeypatch.setattr(llm, "structured", TwoReaders())
    monkeypatch.setattr(httpx, "post", _never_called)
    checked = read_text()
    assert checked.status is CrossCheckStatus.UNAVAILABLE and "presupuesto" in (checked.error or "")


def test_an_image_goes_to_the_second_reader_as_the_image_not_as_the_transcript(readers: TwoReaders) -> None:
    photo = render_invoice(make_spec(channel=InvoiceSource.WHATSAPP))
    invoice = extract_document(photo.data, filename=photo.filename, media_type=photo.media_type, document_id="img")
    [call] = readers.second_calls()
    assert [block["type"] for block in call["content"]] == ["image", "text"]
    assert invoice.cross_check is not None
    readers_of_amount = [r.reader for r in field_check(invoice.cross_check, "amount").readings]
    assert "etiquetas" not in readers_of_amount  # a transcript is not the document's own text


def test_the_same_document_is_read_once_by_the_second_reader(readers: TwoReaders) -> None:
    read_text()
    read_text()
    assert len(readers.second_calls()) == 1


def test_without_a_model_there_is_no_second_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cross_check, "start", REAL_START)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert extract_text(TEXT, document_id="doc").cross_check is None


# Gemini as the second reader ------------------------------------------------------------------------------------


def gemini_answer(reading: CriticalReading, *, finish: str = "STOP") -> httpx.Response:
    body = {
        "candidates": [{"finishReason": finish, "content": {"parts": [{"text": reading.model_dump_json()}]}}],
        "usageMetadata": {"promptTokenCount": 1200, "candidatesTokenCount": 200},
    }
    return httpx.Response(200, json=body)


@dataclass
class FakeGemini:
    response: httpx.Response
    requests: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, url: str, **kwargs: Any) -> httpx.Response:
        self.requests.append({"url": url, **kwargs})
        return self.response


@pytest.fixture
def gemini_reader(readers: TwoReaders, monkeypatch: pytest.MonkeyPatch) -> FakeGemini:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-for-doubles")
    fake = FakeGemini(gemini_answer(second()))
    monkeypatch.setattr(httpx, "post", fake)
    return fake


def test_with_gemini_the_second_reader_is_gemini_and_only_two_readers_vote(
    readers: TwoReaders, gemini_reader: FakeGemini
) -> None:
    checked = read_text()
    assert checked.status is CrossCheckStatus.AGREE
    assert [r.reader for r in field_check(checked, "amount").readings] == ["claude-sonnet-5-5", "gemini-2.5-flash"]
    assert readers.second_calls() == []
    [request] = gemini_reader.requests
    assert "gemini-2.5-flash:generateContent" in request["url"]
    assert request["headers"]["x-goog-api-key"] == "test-key-for-doubles"
    config = request["json"]["generationConfig"]
    assert config["thinkingConfig"]["thinkingBudget"] < config["maxOutputTokens"]


def test_gemini_spend_counts_against_the_daily_budget(gemini_reader: FakeGemini) -> None:
    before = llm.budget.spent_today()
    read_text()
    assert llm.budget.spent_today() > before


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, json={"error": "boom"}),
        gemini_answer(second(), finish="SAFETY"),
        httpx.Response(200, json={"candidates": []}),
        httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{"}]}}]}),
    ],
)
def test_a_gemini_failure_is_unavailable_and_never_leaks_the_key(
    gemini_reader: FakeGemini, response: httpx.Response
) -> None:
    gemini_reader.response = response
    checked = read_text()
    assert checked.status is CrossCheckStatus.UNAVAILABLE
    assert "test-key-for-doubles" not in (checked.error or "")


def test_a_gemini_disagreement_is_reported(gemini_reader: FakeGemini) -> None:
    gemini_reader.response = gemini_answer(second(amount="420000.00"))
    checked = read_text()
    assert checked.status is CrossCheckStatus.DISAGREE and not field_check(checked, "amount").agree


def _raise_budget() -> None:
    raise llm.LLMBudgetExceeded("tope")


def _never_called(*args: object, **kwargs: object) -> httpx.Response:
    raise AssertionError("Gemini must not be called without budget")
