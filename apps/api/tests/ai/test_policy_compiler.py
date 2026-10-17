from decimal import Decimal
from typing import Any

import pytest

from custodio import llm
from custodio.ai import compile_policy
from custodio.contracts import AgreementKind

from .conftest import FakeLLM, make_policy, recorded


def change(**fields: Any) -> dict[str, Any]:
    blank: dict[str, Any] = {
        "field": "",
        "source_quote": "",
        "amount": None,
        "currency": None,
        "percent": None,
        "days": None,
        "currencies": [],
        "operation": "set",
        "beneficiary_id": None,
        "agreement_kind": None,
        "allowed": None,
        "approver_name": None,
    }
    return blank | fields


def draft(*changes: dict[str, Any], unsupported: list[str] | None = None, questions: list[str] | None = None) -> Any:
    return {"changes": list(changes), "unsupported": unsupported or [], "questions": questions or []}


def test_a_threshold_sentence_becomes_one_change_with_its_quote(fake_llm: FakeLLM) -> None:
    text = "Nada sobre 3.000 dólares sin aprobación."
    fake_llm.reply(
        draft(
            change(
                field="approval_threshold",
                amount="3000",
                currency="USD",
                source_quote="Nada sobre 3.000 dólares sin aprobación",
            )
        )
    )

    proposal = compile_policy(text, make_policy())

    assert [c.field for c in proposal.changes] == ["approval_threshold"]
    assert proposal.changes[0].before == 5000.0
    assert proposal.changes[0].after == 3000.0
    assert proposal.changes[0].source_quote == "Nada sobre 3.000 dólares sin aprobación"
    assert "R9" in proposal.changes[0].label
    assert proposal.proposed.approval_threshold == Decimal("3000")
    assert proposal.proposed.version == 2
    assert proposal.unsupported == []
    assert proposal.simulation is None


def test_everything_the_text_does_not_touch_stays_identical(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(draft(change(field="reserve", amount="80000", source_quote="deja siempre 80 mil de colchón")))

    proposal = compile_policy("Deja siempre 80 mil de colchón.", current)

    untouched = proposal.proposed.model_dump(exclude={"reserve", "version"})
    assert untouched == current.model_dump(exclude={"reserve", "version"})
    assert proposal.proposed.reserve == Decimal("80000")


def test_an_unknown_field_goes_to_unsupported_and_changes_nothing(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(recorded("compiler_unknown_field"))

    proposal = compile_policy("No pagues más de 3 facturas por día.", current)

    assert proposal.changes == []
    assert len(proposal.unsupported) == 1
    assert "No pagues más de 3 facturas por día" in proposal.unsupported[0]
    assert proposal.proposed == current


def test_a_negative_value_is_rejected_and_asked_about(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(recorded("compiler_negative_reserve"))

    proposal = compile_policy("La reserva es menos 500.", current)

    assert proposal.changes == []
    assert proposal.proposed.reserve == current.reserve
    assert any("reserva" in question.lower() for question in proposal.questions)


def test_a_change_whose_quote_is_not_in_the_text_is_discarded(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(recorded("compiler_invented_quote"))

    proposal = compile_policy("No pagues en reales.", current)

    assert [c.field for c in proposal.changes] == ["allowed_currencies"]
    assert proposal.proposed.per_payment_limit == current.per_payment_limit
    assert any("Límite por pago" in item for item in proposal.unsupported)


def test_an_amount_the_quote_does_not_state_is_discarded(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(recorded("compiler_amount_not_in_quote"))

    proposal = compile_policy("No pagues en reales y sé más flexible.", current)

    assert proposal.proposed.period_budget == current.period_budget
    assert "BRL" not in proposal.proposed.allowed_currencies
    assert any("Cupo de pago automático" in item for item in proposal.unsupported)


def test_spanish_number_words_count_as_evidence(fake_llm: FakeLLM) -> None:
    fake_llm.reply(draft(change(field="approval_threshold", amount="3000", source_quote="nada sobre tres mil dólares")))

    proposal = compile_policy("Nada sobre tres mil dólares sin que lo apruebe Ana.", make_policy())

    assert proposal.proposed.approval_threshold == Decimal("3000")


def test_removing_a_currency_keeps_the_others(fake_llm: FakeLLM) -> None:
    fake_llm.reply(
        draft(
            change(
                field="allowed_currencies", operation="remove", currencies=["BRL"], source_quote="no pagues en reales"
            )
        )
    )

    proposal = compile_policy("No pagues en reales.", make_policy())

    assert proposal.proposed.allowed_currencies == ["USD", "COP", "MXN", "CLP"]
    assert proposal.changes[0].before == ["USD", "COP", "MXN", "BRL", "CLP"]
    assert proposal.changes[0].after == ["USD", "COP", "MXN", "CLP"]


def test_the_base_currency_cannot_be_removed(fake_llm: FakeLLM) -> None:
    fake_llm.reply(
        draft(
            change(field="allowed_currencies", operation="remove", currencies=["USD"], source_quote="nada en dólares")
        )
    )

    proposal = compile_policy("Nada en dólares.", make_policy())

    assert "USD" in proposal.proposed.allowed_currencies
    assert proposal.changes == []
    assert proposal.questions


def test_a_monthly_cap_for_a_known_beneficiary_becomes_its_agreement(fake_llm: FakeLLM) -> None:
    text = "A Nube S.A.S. páguele hasta 9.000 al mes."
    fake_llm.reply(
        draft(
            change(
                field="agreement",
                beneficiary_id="nube",
                agreement_kind="monthly_cap",
                amount="9000",
                source_quote="A Nube S.A.S. páguele hasta 9.000 al mes",
            )
        )
    )

    proposal = compile_policy(text, make_policy())

    assert proposal.changes[0].field == "beneficiaries[nube].agreement"
    assert proposal.changes[0].before is None
    assert proposal.changes[0].after["kind"] == "monthly_cap"
    nube = next(b for b in proposal.proposed.beneficiaries if b.id == "nube")
    assert nube.agreement is not None
    assert nube.agreement.kind is AgreementKind.MONTHLY_CAP
    assert nube.agreement.amount == Decimal("9000")
    assert nube.agreement.currency == "USD"


def test_an_unknown_beneficiary_is_a_question(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(
        draft(
            change(
                field="agreement",
                beneficiary_id="ghost",
                agreement_kind="fixed",
                amount="2500",
                source_quote="el arriendo son 2.500 fijos",
            )
        )
    )

    proposal = compile_policy("El arriendo son 2.500 fijos.", current)

    assert proposal.changes == []
    assert proposal.proposed == current
    assert proposal.questions


def test_a_threshold_in_another_currency_is_asked_not_converted(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(
        draft(change(field="per_payment_limit", amount="20000000", currency="COP", source_quote="20 millones de pesos"))
    )

    proposal = compile_policy("Ningún pago de más de 20 millones de pesos.", current)

    assert proposal.changes == []
    assert proposal.proposed.per_payment_limit == current.per_payment_limit
    assert any("USD" in question for question in proposal.questions)


def test_two_values_for_the_same_rule_are_a_question(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(
        draft(
            change(field="reserve", amount="80000", source_quote="reserva de 80 mil"),
            change(field="reserve", amount="90000", source_quote="mejor 90 mil"),
        )
    )

    proposal = compile_policy("Reserva de 80 mil, no, mejor 90 mil.", current)

    assert proposal.changes == []
    assert proposal.proposed.reserve == current.reserve
    assert any("80" in q and "90" in q for q in proposal.questions)


def test_blocking_a_beneficiary_and_adding_an_approver(fake_llm: FakeLLM) -> None:
    fake_llm.reply(
        draft(
            change(field="allowed", beneficiary_id="litoral", allowed=False, source_quote="no le pagues más a Litoral"),
            change(
                field="approvers",
                operation="add",
                approver_name="Carlos Pérez",
                source_quote="que apruebe Carlos Pérez",
            ),
        )
    )

    proposal = compile_policy("No le pagues más a Litoral; que apruebe Carlos Pérez.", make_policy())

    litoral = next(b for b in proposal.proposed.beneficiaries if b.id == "litoral")
    assert litoral.allowed is False
    assert [a.name for a in proposal.proposed.approvers] == ["Ana Restrepo", "Carlos Pérez"]
    assert {c.field for c in proposal.changes} == {"beneficiaries[litoral].allowed", "approvers"}


def test_percentages_and_days_are_range_checked(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(
        draft(
            change(field="agreement_tolerance_pct", percent="150", source_quote="tolerancia del 150 %"),
            change(field="min_confidence", percent="95", source_quote="confianza del 95 %"),
            change(field="duplicate_window_days", days=0, source_quote="ventana de 0 días"),
        )
    )

    proposal = compile_policy("Tolerancia del 150 %, confianza del 95 % y ventana de 0 días.", current)

    assert proposal.proposed.agreement_tolerance_pct == current.agreement_tolerance_pct
    assert proposal.proposed.min_confidence == Decimal("0.95")
    assert proposal.proposed.duplicate_window_days == current.duplicate_window_days
    assert len(proposal.questions) == 2


def test_the_model_unsupported_and_questions_reach_the_user(fake_llm: FakeLLM) -> None:
    fake_llm.reply(
        draft(unsupported=["«los viernes no pagues»: no hay regla por día"], questions=["¿Pesos de qué país?"])
    )

    proposal = compile_policy("Los viernes no pagues. Tope de 3 millones de pesos.", make_policy())

    assert proposal.unsupported == ["«los viernes no pagues»: no hay regla por día"]
    assert proposal.questions == ["¿Pesos de qué país?"]


def test_irrelevant_text_proposes_nothing(fake_llm: FakeLLM) -> None:
    current = make_policy()
    fake_llm.reply(draft())

    proposal = compile_policy("Hola, ¿cómo va todo por allá?", current)

    assert proposal.changes == []
    assert proposal.proposed == current


def test_blank_text_never_calls_the_model(fake_llm: FakeLLM) -> None:
    proposal = compile_policy("   ", make_policy())

    assert fake_llm.calls == []
    assert proposal.changes == []


def test_the_compiler_uses_the_smart_model_and_never_shows_account_numbers(fake_llm: FakeLLM) -> None:
    fake_llm.reply(draft())

    compile_policy("Tope de 3.000.", make_policy())

    call = fake_llm.calls[0]
    assert call.model == "claude-opus-5-5"
    assert call.effort == "high"
    assert "Tope de 3.000." in call.text
    assert "Nube S.A.S." in call.text
    assert "12345678901" not in call.text
    assert "12345678901" not in call.system


def test_a_model_failure_is_not_turned_into_a_guess(fake_llm: FakeLLM) -> None:
    fake_llm.reply(llm.LLMRefused("no"))

    with pytest.raises(llm.LLMRefused):
        compile_policy("Tope de 3.000.", make_policy())
