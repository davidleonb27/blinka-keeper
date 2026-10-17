from custodio import llm
from custodio.ai import narrate
from custodio.contracts import RuleOutcome

from .conftest import FakeLLM, make_decision, recorded

ESCALATED = make_decision(
    failing={"R9": (RuleOutcome.ESCALATE, "12.500 USD supera el tope de aprobación automática de 5.000 USD.")}
)


def test_a_narration_whose_numbers_all_come_from_the_acta_is_returned(fake_llm: FakeLLM) -> None:
    text = (
        "Custodio no pagó solo esta factura de Nube S.A.S. por 12.500 USD porque pasa del tope de 5.000 USD "
        "que la empresa fijó para pagar sin preguntar. Una persona debe aprobarla."
    )
    fake_llm.reply({"text": text})

    assert narrate(ESCALATED) == text


def test_numbers_written_in_another_format_still_match(fake_llm: FakeLLM) -> None:
    text = "La factura es de 12,500.00 USD y el tope es 5 mil USD; las 12 reglas se revisaron."
    fake_llm.reply({"text": text})

    assert narrate(ESCALATED) == text


def test_an_invented_number_falls_back_to_the_engine_explanation(fake_llm: FakeLLM) -> None:
    fake_llm.reply(recorded("narrator_invented_number"))

    assert narrate(ESCALATED) == ESCALATED.explanation


def test_a_derived_number_is_also_rejected(fake_llm: FakeLLM) -> None:
    fake_llm.reply({"text": "La factura se pasa del tope por 7.500 USD."})

    assert narrate(ESCALATED) == ESCALATED.explanation


def test_an_empty_narration_falls_back(fake_llm: FakeLLM) -> None:
    fake_llm.reply({"text": "   "})

    assert narrate(ESCALATED) == ESCALATED.explanation


def test_a_model_failure_falls_back(fake_llm: FakeLLM) -> None:
    fake_llm.reply(llm.LLMTruncated("cut"))

    assert narrate(ESCALATED) == ESCALATED.explanation


def test_the_narrator_uses_the_fast_model_at_low_effort_and_sees_the_acta(fake_llm: FakeLLM) -> None:
    fake_llm.reply({"text": "Se pidió aprobación."})

    narrate(ESCALATED)

    call = fake_llm.calls[0]
    assert call.model == "claude-sonnet-5-5"
    assert call.effort == "low"
    assert "supera el tope de aprobación automática" in call.text
