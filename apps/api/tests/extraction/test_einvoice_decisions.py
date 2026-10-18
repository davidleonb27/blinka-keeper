"""The demo electronic invoices through the real engine: the official XML goes the same way as any other reading."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from custodio.contracts import AgentVerdict, ExtractedInvoice, InvoiceCase, InvoiceSpec, RuleOutcome
from custodio.dataset import demo_company
from custodio.dataset.einvoices import DEMO_CFDI, DEMO_FILES
from custodio.engine import decide_all
from custodio.extraction import extract_document, render_invoice
from custodio.extraction.einvoice import merge, read_einvoice


def decide(extraction: ExtractedInvoice) -> dict[str, RuleOutcome | AgentVerdict]:
    state, policy = demo_company()
    case = InvoiceCase(id="XML-1", received_at=datetime(2026, 10, 16, 9, tzinfo=UTC), extraction=extraction)
    decision = decide_all([case], state, policy).decisions[0]
    return {"verdict": decision.agent_verdict, **{rule.rule_id: rule.outcome for rule in decision.rules}}


def demo_reading(name: str) -> ExtractedInvoice:
    state, _ = demo_company()
    return read_einvoice(DEMO_FILES[name].encode(), document_id=name, company_name=state.company_name)


def test_the_valid_dian_invoice_is_paid_on_its_own() -> None:
    outcome = decide(demo_reading("dian-ruta-legal-valida.xml"))

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


def test_the_cfdi_with_its_rendered_pdf_is_paid_on_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # the PDF is read by code from its labelled lines
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    _, policy = demo_company()
    colibri = next(b for b in policy.beneficiaries if b.tax_id == DEMO_CFDI.supplier_rfc)
    spec = InvoiceSpec(
        supplier_name=colibri.name,
        supplier_tax_id=colibri.tax_id,
        tax_label="RFC",
        invoice_number="CA-2210",
        issue_date=date(2026, 10, 15),
        amount=Decimal("46000"),
        currency="MXN",
        bank_name=colibri.bank_name,
        account_number=colibri.account_number,
        description=DEMO_CFDI.description,
    )
    rendered = render_invoice(spec)
    pdf = extract_document(rendered.data, filename=rendered.filename, media_type=rendered.media_type, document_id="p")

    outcome = decide(merge(demo_reading("cfdi-colibri-analitica.xml"), pdf))

    assert outcome["verdict"] is AgentVerdict.PAY, outcome
