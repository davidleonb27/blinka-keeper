"""A supplier's confirmation read by the real reader, then decided by the real rules. CUSTODIO_LIVE_TESTS=1 runs it.

The demo invoice F-039 stopped because the amount of a phone photo could not be read; the supplier confirms it and
the corrected text must be read with verified quotes, so the same fifteen rules pay it alone.
"""

import pytest

from custodio import dataset, engine
from custodio.contracts import InvoiceCase, InvoiceSource, RuleOutcome
from custodio.corrections import CorrectableField, corrected_text
from custodio.corrections.demo import seed_cases
from custodio.extraction import extract_text

pytestmark = pytest.mark.live


def test_a_confirmed_amount_is_read_with_verified_quotes_and_paid_alone() -> None:
    state, policy = dataset.demo_company()
    (stopped,) = seed_cases(policy, state.company_name)
    text = corrected_text(stopped.extraction, {CorrectableField.AMOUNT: "1.900,00"})

    reading = extract_text(text, document_id="live-correction", source=InvoiceSource.TEXT)

    assert reading.amount.value is not None and float(reading.amount.value) == 1900
    assert reading.amount.verified and reading.account_number.verified
    case = InvoiceCase(id="F-039-C1", received_at=stopped.received_at, extraction=reading)
    decision = engine.decide_all([case], state, policy).decisions[0]
    assert next(rule for rule in decision.rules if rule.rule_id == "R1").outcome is RuleOutcome.PASS
    assert decision.status.value == "paid_auto"
