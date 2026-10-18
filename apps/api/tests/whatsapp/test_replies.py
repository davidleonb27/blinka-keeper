from custodio.whatsapp import replies


def test_a_company_name_ending_in_a_period_does_not_double_it() -> None:
    reply = replies.linked("Cobalto Labs, Inc.")

    assert "Cobalto Labs, Inc. Envía" in reply
    assert ".." not in reply
