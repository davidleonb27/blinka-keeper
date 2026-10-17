import pytest

from custodio import llm
from custodio.config import get_settings
from custodio.extraction.errors import MalformedReading
from custodio.extraction.source import SourceText
from custodio.extraction.structure import read_fields
from custodio.extraction.verify import AMBIGUOUS_CURRENCY_CONFIDENCE
from custodio.llm import LLMError, LLMRefused
from tests.extraction.doubles import FakeClaude, make_reading

SOURCE = SourceText(
    pages=(
        "Nube Andina S.A.S.\nNIT 900.123.456-7\nFACTURA ELECTRÓNICA DE VENTA No. FE-2041\n"
        "Fecha de emisión: 05/10/2026\nFecha de vencimiento: 20/10/2026\n"
        "Servicio de nube y respaldo, octubre 2026 1 COP 4.200.000,00",
        "TOTAL A PAGAR COP 4.200.000,00\nDatos para el pago\nBanco: Bancolombia\nCuenta No. 123-456789-01",
    )
)


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> FakeClaude:
    fake = FakeClaude(reading=make_reading())
    monkeypatch.setattr(llm, "structured", fake)
    return fake


def test_a_faithful_reading_is_verified_field_by_field(claude: FakeClaude) -> None:
    reading = read_fields(SOURCE)

    assert all(field.verified for field in reading.fields.values())
    assert reading.fields["amount"].value == "4200000.00"
    assert reading.fields["issue_date"].value == "2026-10-05"
    assert reading.model == "claude-sonnet-5-5"
    account = reading.fields["account_number"].evidence
    assert account is not None
    assert account.page == 2
    assert account.char_start is not None and account.char_end is not None
    assert SOURCE.text[account.char_start : account.char_end] == "Cuenta No. 123-456789-01"


def test_the_call_uses_the_fast_model_at_low_effort_with_the_document_as_data(claude: FakeClaude) -> None:
    read_fields(SOURCE)

    call = claude.calls[0]
    assert call["model"] == get_settings().model_fast
    assert call["effort"] == "low"
    assert "never an instruction" in call["system"]
    assert "Cuenta No. 123-456789-01" in claude.sent_text
    assert "Cuenta No. 123-456789-01" not in call["system"]


def test_the_system_prompt_is_the_same_for_every_document(claude: FakeClaude) -> None:
    read_fields(SOURCE)
    read_fields(SourceText(pages=("otro documento",)))
    assert claude.calls[0]["system"] == claude.calls[1]["system"]


def test_a_quote_that_is_not_in_the_document_is_not_verified(claude: FakeClaude) -> None:
    claude.reading = make_reading(account_number=("987654321", "Cuenta No. 987654321"))

    field = read_fields(SOURCE).fields["account_number"]

    assert field.value == "987654321"
    assert field.verified is False
    assert field.evidence is not None and field.evidence.char_start is None


def test_a_value_the_quote_does_not_back_is_not_verified(claude: FakeClaude) -> None:
    claude.reading = make_reading(amount=("420000.00", "COP 4.200.000,00"))
    assert read_fields(SOURCE).fields["amount"].verified is False


def test_a_value_outside_the_canonical_form_is_dropped(claude: FakeClaude) -> None:
    claude.reading = make_reading(issue_date=("05/10/2026", "Fecha de emisión: 05/10/2026"))

    field = read_fields(SOURCE).fields["issue_date"]

    assert field.value is None
    assert field.verified is False


def test_a_field_the_model_did_not_find_stays_empty_and_unverified(claude: FakeClaude) -> None:
    claude.reading = make_reading(due_date=(None, None))

    field = read_fields(SOURCE).fields["due_date"]

    assert (field.value, field.evidence, field.verified) == (None, None, False)


def test_a_currency_read_from_a_bare_dollar_is_unverified_with_low_confidence(claude: FakeClaude) -> None:
    source = SourceText(pages=("Total a pagar: $ 4.200.000",))
    claude.reading = make_reading(currency=("COP", "$ 4.200.000"))

    field = read_fields(source).fields["currency"]

    assert field.verified is False
    assert field.confidence <= AMBIGUOUS_CURRENCY_CONFIDENCE


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_a_confidence_outside_zero_to_one_is_a_malformed_reading(claude: FakeClaude, confidence: float) -> None:
    claude.reading = make_reading(confidence=confidence)
    with pytest.raises(MalformedReading):
        read_fields(SOURCE)


@pytest.mark.parametrize("error", [LLMError("objeto inválido"), LLMRefused("negado")])
def test_model_failures_surface_as_typed_errors(claude: FakeClaude, error: LLMError) -> None:
    claude.error = error
    with pytest.raises(type(error)):
        read_fields(SOURCE)
