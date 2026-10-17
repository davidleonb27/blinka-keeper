"""Small builders for engine tests: one company, one beneficiary, invoices read perfectly unless told otherwise."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from custodio.contracts import (
    Agreement,
    AgreementKind,
    Approval,
    Beneficiary,
    CompanyState,
    Decision,
    Evidence,
    ExtractedField,
    ExtractedInvoice,
    HiddenTextFinding,
    HiddenTextKind,
    InvoiceCase,
    InvoiceSource,
    PaymentRecord,
    Policy,
    RuleResult,
)
from custodio.engine.domains import first_email

TODAY = date(2026, 10, 16)
FX = {"USD": Decimal(1), "COP": Decimal(4100), "MXN": Decimal("18.4"), "BRL": Decimal("5.4"), "EUR": Decimal("0.92")}
ANDES_ACCOUNT = "0012-4821"


def agreement(amount: str = "4800", currency: str = "USD", *, kind: AgreementKind = AgreementKind.FIXED) -> Agreement:
    return Agreement(kind=kind, amount=Decimal(amount), currency=currency)


def beneficiary(
    bid: str = "b1",
    name: str = "Andes Code SAS",
    tax_id: str = "901.482.337-1",
    *,
    account: str = ANDES_ACCOUNT,
    currency: str = "USD",
    deal: Agreement | None = None,
    allowed: bool = True,
    aliases: tuple[str, ...] = (),
    country: str | None = None,
    email_domain: str | None = None,
    contact: str | None = None,
) -> Beneficiary:
    return Beneficiary(
        id=bid,
        name=name,
        tax_id=tax_id,
        aliases=list(aliases),
        country=country,
        bank_name="Bancolombia",
        account_number=account,
        currency=currency,
        agreement=deal,
        allowed=allowed,
        approver_contact=contact,
        email_domain=email_domain,
    )


ANDES = beneficiary(deal=agreement())


def policy(*beneficiaries: Beneficiary, **overrides: object) -> Policy:
    return Policy.model_validate({"beneficiaries": list(beneficiaries) or [ANDES], **overrides})


def state(*history: PaymentRecord, balance: str = "140000") -> CompanyState:
    return CompanyState(
        workspace_id="w-test",
        company_name="Cobalto Labs, Inc.",
        today=TODAY,
        opening_balance=Decimal(balance),
        fx_units_per_base=FX,
        history=list(history),
    )


def paid(
    amount: str,
    *,
    on: date,
    beneficiary_id: str = "b1",
    number: str | None = None,
    currency: str = "USD",
    by: str = "agent",
) -> PaymentRecord:
    value = Decimal(amount)
    return PaymentRecord.model_validate(
        {
            "invoice_id": f"H-{number or amount}",
            "beneficiary_id": beneficiary_id,
            "invoice_number": number,
            "amount": value,
            "currency": currency,
            "amount_base": value / FX[currency],
            "paid_on": on,
            "by": by,
        }
    )


def field(
    value: str | None, *, quote: str | None = None, confidence: float = 0.98, verified: bool = True
) -> ExtractedField:
    evidence = Evidence(quote=quote if quote is not None else value) if value is not None else None
    return ExtractedField(value=value, evidence=evidence, confidence=confidence, verified=verified)


def invoice(
    case_id: str = "F-001",
    *,
    day: int = 1,
    month: int = 10,
    supplier: str | None = "Andes Code SAS",
    tax_id: str | None = "901.482.337-1",
    number: str | None = "AC-2026-10",
    amount: str | None = "4800.00",
    currency: str | None = "USD",
    account: str | None = ANDES_ACCOUNT,
    currency_quote: str | None = None,
    confidence: dict[str, float] | None = None,
    unverified: frozenset[str] = frozenset(),
    note: str | None = None,
    hidden: str | None = None,
    hour: int = 9,
    sender: str | None = None,
) -> InvoiceCase:
    confidences = confidence or {}

    def read(name: str, value: str | None, quote: str | None = None) -> ExtractedField:
        return field(value, quote=quote, confidence=confidences.get(name, 0.98), verified=name not in unverified)

    visible = "\n".join(
        line
        for line in (
            f"De: {sender}" if sender else None,
            f"FACTURA N° {number}",
            f"Emisor: {supplier}",
            f"NIT: {tax_id}",
            f"Total: {currency_quote or f'{currency} {amount}'}",
            f"Pagar a: Bancolombia {account}",
            note,
        )
        if line
    )
    extraction = ExtractedInvoice(
        document_id=f"doc-{case_id}",
        source=InvoiceSource.PDF,
        supplier_name=read("supplier_name", supplier),
        supplier_tax_id=read("supplier_tax_id", tax_id),
        invoice_number=read("invoice_number", number),
        issue_date=read("issue_date", f"2026-{month:02d}-{day:02d}"),
        due_date=read("due_date", None),
        amount=read("amount", amount),
        currency=read("currency", currency, currency_quote),
        bank_name=read("bank_name", "Bancolombia"),
        account_number=read("account_number", account),
        description=read("description", "Equipo de desarrollo"),
        visible_text=visible,
        sender_email=first_email(visible),
        hidden_findings=[hidden_finding(hidden)] if hidden else [],
        reader="test",
        overall_confidence=min([0.98, *confidences.values()]),
    )
    return InvoiceCase(id=case_id, received_at=datetime(2026, month, day, hour, tzinfo=UTC), extraction=extraction)


def hidden_finding(text: str) -> HiddenTextFinding:
    return HiddenTextFinding(
        kind=HiddenTextKind.INVISIBLE_COLOR, text=text, page=1, detail="Texto blanco sobre fondo blanco."
    )


def approval(invoice_id: str, *, approved: bool = True, minute: int = 0, approver: str = "Ana Gómez") -> Approval:
    return Approval(
        invoice_id=invoice_id,
        decision="approved" if approved else "rejected",
        approver=approver,
        channel="web",
        at=datetime(2026, 10, 16, 15, minute, tzinfo=UTC),
    )


def rule(decision: Decision, rule_id: str) -> RuleResult:
    return next(result for result in decision.rules if result.rule_id == rule_id)


def squeezed_by_a_later_payment() -> tuple[list[InvoiceCase], CompanyState]:
    """F-001 (USD 6.500) escalates while the reserve still allows it; F-002 (USD 4.000) is then paid alone, so at
    approval time paying F-001 would leave USD 59.500, under the USD 60.000 reserve."""
    cases = [invoice("F-001", amount="6500.00"), invoice("F-002", day=5, number="AC-2026-10B", amount="4000.00")]
    return cases, state(balance="70000")
