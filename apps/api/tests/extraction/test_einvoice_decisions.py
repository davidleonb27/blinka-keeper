"""The demo electronic invoices through the real engine: the official XML goes the same way as any other reading."""

from datetime import UTC, datetime

from custodio.contracts import AgentVerdict, ExtractedInvoice, InvoiceCase, RuleOutcome
from custodio.dataset import demo_company
from custodio.dataset.einvoices import DEMO_FILES
from custodio.engine import decide_all
from custodio.extraction.einvoice import read_einvoice


def decide(extraction: ExtractedInvoice) -> dict[str, RuleOutcome | AgentVerdict]:
    state, policy = demo_company()
    case = InvoiceCase(id="XML-1", received_at=datetime(2026, 10, 16, 9, tzinfo=UTC), extraction=extraction)
    decision = decide_all([case], state, policy).decisions[0]
    return {"verdict": decision.agent_verdict, **{rule.rule_id: rule.outcome for rule in decision.rules}}


def demo_reading(name: str) -> ExtractedInvoice:
    state, _ = demo_company()
    return read_einvoice(DEMO_FILES[name].encode(), document_id=name, company_name=state.company_name)


def test_the_valid_dian_invoice_is_paid_on_its_own() -> None:
    outcome = decide(demo_reading("dian-distrito-norte-valida.xml"))

    assert outcome["verdict"] is AgentVerdict.PAY
    assert outcome["R1"] is RuleOutcome.PASS


def test_the_dian_invoice_with_a_wrong_check_digit_is_not_paid() -> None:
    outcome = decide(demo_reading("dian-estudio-lumbre-nit-invalido.xml"))

    assert outcome["verdict"] is AgentVerdict.ESCALATE
    assert outcome["R1"] is RuleOutcome.ESCALATE
    assert outcome["R13"] is RuleOutcome.ESCALATE


def test_the_cfdi_alone_waits_for_its_bank_account() -> None:
    outcome = decide(demo_reading("cfdi-colibri-analitica.xml"))

    assert outcome["verdict"] is AgentVerdict.ESCALATE
    assert outcome["R1"] is RuleOutcome.ESCALATE
