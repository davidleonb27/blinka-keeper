"""The independent auditor: every payment is recomputed from the raw cases by a code path of its own.

It shares vocabulary with the engine (how to compare names and codes, how to read an amount, which phrases address
an agent, which check digits an account follows, how a name compares with the sanctions list, when two domains look
alike) and nothing else: it never imports the rules or decide_all, keeps its own running totals and identifies
suppliers on its own. A payment with any problem is improper; decide_all then vetoes it, so the auditor always wins.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from custodio.contracts import (
    AgreementKind,
    AuditFinding,
    AuditReport,
    BatchResult,
    Beneficiary,
    CompanyState,
    Decision,
    DecisionStatus,
    ExtractedField,
    ExtractedInvoice,
    InvoiceCase,
    PaymentRecord,
    Policy,
)
from custodio.engine.bank_details import Check, account_checks, tax_id_check
from custodio.engine.domains import DomainLikeness, compare_domains, email_domain
from custodio.engine.injection import find_instruction
from custodio.engine.sanctions import SanctionsList, bundled_sanctions
from custodio.engine.text import normalize_code, normalize_name
from custodio.engine.units import as_utc, parse_amount, to_base

SAME_AMOUNT = Decimal("0.005")
HUNDRED = Decimal(100)
TRUSTED_FIELDS = {"supplier_name": "proveedor", "amount": "monto", "currency": "moneda", "account_number": "cuenta"}
DOLLAR_PREFIXES = {"US": "USD", "R": "BRL", "MX": "MXN", "COL": "COP", "CLP": "CLP"}
NEVER = datetime.min.replace(tzinfo=UTC)  # sorts a forged human payment without approval first
COUNTRY_OF_CURRENCY = {"COP": "CO", "MXN": "MX", "BRL": "BR"}


@dataclass(frozen=True)
class _Invoice:
    """A case as the auditor reads it, on its own."""

    case: InvoiceCase
    order: int
    day: date
    payee: Beneficiary | None
    number: str
    amount: Decimal | None
    currency: str | None
    base: Decimal | None


@dataclass
class _Totals:
    """Running totals the auditor keeps for itself while it walks the payments."""

    balance: Decimal
    agent_by_month: defaultdict[tuple[int, int], Decimal]
    agent_paid: list[_Invoice]


def audit(
    batch: BatchResult,
    cases: Sequence[InvoiceCase],
    state: CompanyState,
    policy: Policy,
    *,
    sanctions: SanctionsList | None = None,
) -> AuditReport:
    listed = sanctions or bundled_sanctions()
    invoices = _read(cases, state, policy)
    autonomous, by_person = _payments(batch.decisions, invoices)
    totals = _Totals(balance=state.opening_balance, agent_by_month=_agent_history(state), agent_paid=[])
    findings = [
        finding
        for invoice in autonomous
        if (finding := _finding(invoice, _autonomous_problems(invoice, invoices, state, policy, totals, listed)))
    ]
    findings += [
        finding
        for decision, invoice in by_person
        if (finding := _finding(invoice, _human_problems(decision, invoice, invoices, state, policy, totals)))
    ]
    findings += [_unknown(d) for d in batch.decisions if _is_payment(d) and d.invoice_id not in invoices]
    return AuditReport(
        agrees=not findings,
        checked=sum(1 for d in batch.decisions if _is_payment(d)),
        improper_payments=len(findings),
        findings=findings,
    )


# Reading -------------------------------------------------------------------------------------------------------


def _read(cases: Sequence[InvoiceCase], state: CompanyState, policy: Policy) -> dict[str, _Invoice]:
    ordered = sorted(enumerate(cases), key=lambda item: (as_utc(item[1].received_at), item[0]))
    invoices = {}
    for order, (_, case) in enumerate(ordered):
        read = case.extraction
        amount = parse_amount(read.amount.value)
        currency = read.currency.value.strip().upper() if read.currency.value else None
        invoices[case.id] = _Invoice(
            case=case,
            order=order,
            day=as_utc(case.received_at).date(),
            payee=_identify(read.supplier_name.value, read.supplier_tax_id.value, policy),
            number=normalize_code(read.invoice_number.value or ""),
            amount=amount,
            currency=currency,
            base=to_base(amount, currency, state.fx_units_per_base),
        )
    return invoices


def _identify(name: str | None, tax_id: str | None, policy: Policy) -> Beneficiary | None:
    """By tax id when one was read, by name or alias otherwise; any name pointing elsewhere voids the match."""
    wanted_name = normalize_name(name or "")
    named = [b for b in policy.beneficiaries if wanted_name and wanted_name in _names(b)]
    wanted_tax_id = normalize_code(tax_id or "")
    if not wanted_tax_id:
        return named[0] if len(named) == 1 else None
    taxed = [b for b in policy.beneficiaries if normalize_code(b.tax_id) == wanted_tax_id]
    if len(taxed) != 1 or any(b.id != taxed[0].id for b in named):
        return None
    return taxed[0]


def _names(beneficiary: Beneficiary) -> set[str]:
    return {normalize_name(name) for name in (beneficiary.name, *beneficiary.aliases)}


def _payments(
    decisions: Sequence[Decision], invoices: dict[str, _Invoice]
) -> tuple[list[_Invoice], list[tuple[Decision, _Invoice]]]:
    autonomous = [
        invoices[d.invoice_id] for d in decisions if d.status is DecisionStatus.PAID_AUTO and d.invoice_id in invoices
    ]
    by_person = [
        (d, invoices[d.invoice_id])
        for d in decisions
        if d.status is DecisionStatus.PAID_HUMAN and d.invoice_id in invoices
    ]
    autonomous.sort(key=lambda invoice: invoice.order)
    by_person.sort(key=lambda pair: (as_utc(pair[0].approval.at) if pair[0].approval else NEVER, pair[1].order))
    return autonomous, by_person


def _agent_history(state: CompanyState) -> defaultdict[tuple[int, int], Decimal]:
    spent: defaultdict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for record in state.history:
        if record.by == "agent":
            spent[_month(record.paid_on)] += record.amount_base
    return spent


# Autonomous payments: all fifteen conditions --------------------------------------------------------------------


def _autonomous_problems(
    invoice: _Invoice,
    invoices: dict[str, _Invoice],
    state: CompanyState,
    policy: Policy,
    totals: _Totals,
    sanctions: SanctionsList,
) -> list[str]:
    problems = [*_reading_problems(invoice.case.extraction, policy), *_instruction_problems(invoice.case.extraction)]
    payee = invoice.payee
    if payee is None or not payee.allowed:
        problems.append("beneficiario no permitido")
    else:
        problems += _account_problems(invoice, payee)
        problems += _agreement_problems(invoice, payee, state, policy, totals)
    problems += _duplicate_problems(invoice, invoices, state, policy)
    problems += _split_problems(invoice, invoices, state, policy)
    problems += _currency_problems(invoice, state, policy)
    problems += [*_details_problems(invoice), *_sanctions_problems(invoice, sanctions), *_sender_problems(invoice)]
    return [*problems, *_money_problems(invoice, state, policy, totals)]


def _money_problems(invoice: _Invoice, state: CompanyState, policy: Policy, totals: _Totals) -> list[str]:
    """Limits, budget and reserve against the auditor's own running totals, which then record this payment."""
    if invoice.base is None:
        return ["sin monto en moneda base"]
    month, problems = _month(invoice.day), []
    if invoice.base > _approval_cap(invoice, state, policy):
        problems.append("sobre el tope de aprobación")
    if invoice.base > policy.per_payment_limit:
        problems.append("sobre el límite por pago")
    if totals.agent_by_month[month] + invoice.base > policy.period_budget:
        problems.append("sin cupo de pago automático")
    if totals.balance - invoice.base < policy.reserve:
        problems.append("toca la reserva")
    totals.balance -= invoice.base
    totals.agent_by_month[month] += invoice.base
    totals.agent_paid.append(invoice)
    return problems


def _approval_cap(invoice: _Invoice, state: CompanyState, policy: Policy) -> Decimal:
    """The cap the supplier earned (looked up by the auditor's own identification), else the policy's."""
    earned = state.trust.get(invoice.payee.id) if invoice.payee else None
    return policy.approval_threshold if earned is None else earned.cap


def _reading_problems(read: ExtractedInvoice, policy: Policy) -> list[str]:
    problems = [
        f"lectura no confiable ({label})"
        for name, label in TRUSTED_FIELDS.items()
        if not _trusted(getattr(read, name), policy.min_confidence)
    ]
    if parse_amount(read.amount.value) is None and "lectura no confiable (monto)" not in problems:
        problems.append("lectura no confiable (monto)")
    if read.supplier_tax_id.value is not None and not _trusted(read.supplier_tax_id, policy.min_confidence):
        problems.append("lectura no confiable (identificación fiscal)")
    if _currency_unclear(read.currency):
        problems.append("moneda ambigua")
    return problems


def _currency_unclear(field: ExtractedField) -> bool:
    """«$» names a currency only next to the code that was read or that code's own prefix (US$, R$, MX$, COL$)."""
    quote = field.evidence.quote.upper() if field.evidence else ""
    if "$" not in quote:
        return False
    code = (field.value or "").strip().upper()
    words = set(re.findall(r"[A-Z]+", quote))
    prefixes = {DOLLAR_PREFIXES.get(word) for word in re.findall(r"([A-Z]+)\$", quote)}
    return code not in words and code not in prefixes


def _trusted(field: ExtractedField, minimum: Decimal) -> bool:
    return field.value is not None and field.verified and Decimal(str(field.confidence)) >= minimum


def _instruction_problems(read: ExtractedInvoice) -> list[str]:
    values = [value.value for value in vars(read).values() if isinstance(value, ExtractedField) and value.value]
    if read.hidden_findings or find_instruction("\n".join([read.visible_text, *values])):
        return ["instrucciones dirigidas al agente"]
    return []


def _account_problems(invoice: _Invoice, payee: Beneficiary) -> list[str]:
    """An unread account is a reading problem; here only a different account counts."""
    read = invoice.case.extraction.account_number.value
    if read is not None and normalize_code(read) != normalize_code(payee.account_number):
        return ["cuenta distinta a la registrada"]
    return []


def _agreement_problems(
    invoice: _Invoice, payee: Beneficiary, state: CompanyState, policy: Policy, totals: _Totals
) -> list[str]:
    deal = payee.agreement
    if deal is None:
        return []
    if invoice.amount is None or invoice.currency != deal.currency:
        return ["moneda distinta a la acordada"]
    if deal.kind is AgreementKind.FIXED:
        tolerance = deal.tolerance_pct if deal.tolerance_pct is not None else policy.agreement_tolerance_pct
        gap = abs(invoice.amount - deal.amount) * HUNDRED
        return [] if deal.amount > 0 and gap <= deal.amount * tolerance else ["no coincide con lo acordado"]
    month = _month(invoice.day)
    history = [
        r.amount for r in _history_of(payee, state) if _month(r.paid_on) == month and r.currency == deal.currency
    ]
    batch = [
        other.amount
        for other in totals.agent_paid
        if other.payee is not None
        and other.payee.id == payee.id
        and _month(other.day) == month
        and other.currency == deal.currency
        and other.amount is not None
    ]
    if sum(history, Decimal(0)) + sum(batch, Decimal(0)) + invoice.amount > deal.amount:
        return ["supera el tope mensual acordado"]
    return []


def _duplicate_problems(
    invoice: _Invoice, invoices: dict[str, _Invoice], state: CompanyState, policy: Policy
) -> list[str]:
    if invoice.payee is None:
        return []
    earlier = [other for other in _same_payee(invoice, invoices) if other.order < invoice.order]
    seen = [(o.number, o.amount, o.currency, o.day) for o in earlier]
    seen += [
        (normalize_code(r.invoice_number or ""), r.amount, r.currency.upper(), r.paid_on)
        for r in _history_of(invoice.payee, state)
    ]
    for number, amount, currency, day in seen:
        if invoice.number and number == invoice.number:
            return ["cobro duplicado (mismo número)"]
        if _same_charge(invoice, amount, currency, day, policy.duplicate_window_days):
            return ["cobro duplicado (mismo monto)"]
    return []


def _same_charge(invoice: _Invoice, amount: Decimal | None, currency: str | None, day: date, window: int) -> bool:
    if invoice.amount is None or amount is None or currency != invoice.currency:
        return False
    return abs(amount - invoice.amount) <= SAME_AMOUNT * invoice.amount and abs((invoice.day - day).days) <= window


def _split_problems(invoice: _Invoice, invoices: dict[str, _Invoice], state: CompanyState, policy: Policy) -> list[str]:
    threshold, window = policy.approval_threshold, policy.split_window_days
    if invoice.payee is None or invoice.base is None or invoice.base > threshold:
        return []
    pieces: dict[str, Decimal] = {}
    for record in _history_of(invoice.payee, state):
        if abs((invoice.day - record.paid_on).days) <= window and record.amount_base <= threshold:
            pieces.setdefault(normalize_code(record.invoice_number or "") or record.invoice_id, record.amount_base)
    for other in _same_payee(invoice, invoices):
        if abs((invoice.day - other.day).days) <= window and other.base is not None and other.base <= threshold:
            pieces.setdefault(other.number or other.case.id, other.base)
    if len(pieces) >= 2 and sum(pieces.values(), Decimal(0)) > threshold:
        return ["pago fraccionado"]
    return []


def _currency_problems(invoice: _Invoice, state: CompanyState, policy: Policy) -> list[str]:
    rate = state.fx_units_per_base.get(invoice.currency or "")
    if invoice.currency not in policy.allowed_currencies or rate is None or rate <= 0:
        return ["moneda no permitida"]
    return []


def _details_problems(invoice: _Invoice) -> list[str]:
    """Check digits of the account and tax id read, and of the registered ones."""
    read, payee = invoice.case.extraction, invoice.payee
    country = payee.country if payee else COUNTRY_OF_CURRENCY.get(invoice.currency or "")
    checks: list[Check | None] = [tax_id_check(read.supplier_tax_id.value or "", country=country)]
    checks += account_checks(read.account_number.value or "", currency=invoice.currency, country=country)
    if payee is not None:
        checks.append(tax_id_check(payee.tax_id, country=payee.country))
        checks += account_checks(payee.account_number, currency=payee.currency, country=payee.country)
    bad = sorted({check.scheme for check in checks if check is not None and not check.valid})
    return [f"datos bancarios o identificación inválidos ({', '.join(bad)})"] if bad else []


def _sanctions_problems(invoice: _Invoice, sanctions: SanctionsList) -> list[str]:
    if sanctions.size == 0:
        return ["no se revisó contra la lista OFAC (0 entradas)"]
    payee = invoice.payee
    names = [invoice.case.extraction.supplier_name.value, *((payee.name, *payee.aliases) if payee else ())]
    if any(name and sanctions.screen(name) is not None for name in names):
        return ["coincide con la lista OFAC"]
    return []


def _sender_problems(invoice: _Invoice) -> list[str]:
    sender, payee = invoice.case.extraction.sender_email, invoice.payee
    if sender is None or payee is None or payee.email_domain is None:
        return []
    if compare_domains(email_domain(sender), payee.email_domain).likeness is DomainLikeness.LOOKALIKE:
        return ["correo de un dominio parecido al registrado"]
    return []


# Payments authorized by a person: hold rules still apply, and the reserve always does --------------------------


def _human_problems(
    decision: Decision,
    invoice: _Invoice,
    invoices: dict[str, _Invoice],
    state: CompanyState,
    policy: Policy,
    totals: _Totals,
) -> list[str]:
    problems = []
    given = decision.approval
    if given is None or given.decision != "approved" or given.invoice_id != decision.invoice_id:
        problems.append("sin aprobación de una persona")
    if invoice.payee is not None:
        problems += _account_problems(invoice, invoice.payee)
    problems += _duplicate_problems(invoice, invoices, state, policy)
    problems += _currency_problems(invoice, state, policy)
    if invoice.base is None:
        return [*problems, "sin monto en moneda base"]
    if totals.balance - invoice.base < policy.reserve:
        problems.append("toca la reserva")
    totals.balance -= invoice.base
    return problems


# Helpers -------------------------------------------------------------------------------------------------------


def _same_payee(invoice: _Invoice, invoices: dict[str, _Invoice]) -> list[_Invoice]:
    payee = invoice.payee
    return [o for o in invoices.values() if payee is not None and o.payee is not None and o.payee.id == payee.id]


def _history_of(payee: Beneficiary, state: CompanyState) -> list[PaymentRecord]:
    return [record for record in state.history if record.beneficiary_id == payee.id]


def _month(day: date) -> tuple[int, int]:
    return (day.year, day.month)


def _is_payment(decision: Decision) -> bool:
    return decision.status in (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN)


def _finding(invoice: _Invoice, problems: list[str]) -> AuditFinding | None:
    if not problems:
        return None
    return AuditFinding(
        invoice_id=invoice.case.id, severity="critical", message=f"Pago indebido: {'; '.join(problems)}."
    )


def _unknown(decision: Decision) -> AuditFinding:
    return AuditFinding(
        invoice_id=decision.invoice_id, severity="critical", message="Pago indebido: la factura no está en el lote."
    )
