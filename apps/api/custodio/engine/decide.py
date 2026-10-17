"""decide_all: every invoice in arrival order, then the people's approvals, then the auditor has the last word."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from custodio.contracts import (
    RULES,
    AgentVerdict,
    Approval,
    AuditReport,
    BatchResult,
    CompanyState,
    Decision,
    DecisionStatus,
    InvoiceCase,
    Policy,
    RuleOutcome,
    RuleResult,
)
from custodio.engine.audit import audit
from custodio.engine.beneficiaries import BeneficiaryMatch, match_beneficiary
from custodio.engine.draft import Draft
from custodio.engine.errors import DuplicateCaseIdError
from custodio.engine.explain import counterfactual, explanation
from custodio.engine.facts import Charge, InvoiceFacts, charge_from_history, charge_from_invoice, read_facts
from custodio.engine.formatting import money
from custodio.engine.metrics import compute_metrics
from custodio.engine.rules import EVALUATORS, RuleContext
from custodio.engine.text import normalize_name
from custodio.engine.units import as_utc

AUDITOR_VETO = "El auditor independiente no confirma este pago: {finding}"
HOLD_RULE_APPROVED = "Una aprobación no levanta una regla de retención: {labels}."
NO_BASE_AMOUNT = "No hay un monto confiable en {base}; no se puede pagar."
RESERVE_BREACH = "Pagarlo dejaría el saldo en {after}, debajo de la reserva de {reserve}."


@dataclass(frozen=True)
class _Supplier:
    """Everything the rules need to know about one supplier's other charges."""

    history: tuple[Charge, ...]
    invoices: tuple[InvoiceFacts, ...]  # in arrival order


def decide_all(
    cases: Sequence[InvoiceCase],
    state: CompanyState,
    policy: Policy,
    approvals: Mapping[str, Approval] | None = None,
) -> BatchResult:
    """Decide, audit, and repeat with the auditor's vetoes until it agrees: when they differ, the auditor wins."""
    vetoes: dict[str, str] = {}
    while True:
        batch, report = _decide_and_audit(cases, state, policy, approvals or {}, vetoes)
        fresh = {f.invoice_id: f.message for f in report.findings if f.invoice_id not in vetoes}
        if not fresh:
            return batch
        vetoes |= fresh


def run_batch(
    cases: Sequence[InvoiceCase],
    state: CompanyState,
    policy: Policy,
    *,
    approvals: Mapping[str, Approval],
    vetoes: Mapping[str, str],
) -> BatchResult:
    """One pass of the engine with the given vetoes, reporting what the auditor thinks of it."""
    return _decide_and_audit(cases, state, policy, approvals, vetoes)[0]


def verdict_of(results: Iterable[RuleResult]) -> AgentVerdict:
    """Hold beats escalate beats pay. A rule that could not be evaluated never lets a payment through alone."""
    outcomes = {result.outcome for result in results}
    if RuleOutcome.HOLD in outcomes:
        return AgentVerdict.HOLD
    if outcomes & {RuleOutcome.ESCALATE, RuleOutcome.SKIPPED}:
        return AgentVerdict.ESCALATE
    return AgentVerdict.PAY


def balance_below_reserve(balance: Decimal, amount_base: Decimal, policy: Policy) -> Decimal | None:
    """The balance a payment would leave when that is under the reserve; None when the payment fits."""
    after = balance - amount_base
    return after if after < policy.reserve else None


def _decide_and_audit(
    cases: Sequence[InvoiceCase],
    state: CompanyState,
    policy: Policy,
    approvals: Mapping[str, Approval],
    vetoes: Mapping[str, str],
) -> tuple[BatchResult, AuditReport]:
    drafts, spent_by_month = _decide_agent(cases, state, policy, vetoes)
    drafts, balance_end = _apply_approvals(drafts, approvals, policy, vetoes, _balance_after_agent(drafts, state))
    decisions = [_finish(draft) for draft in drafts]
    batch = BatchResult(
        decisions=decisions,
        spent_auto_base=spent_by_month[(state.today.year, state.today.month)],
        balance_end=balance_end,
        metrics=compute_metrics(decisions, cases, improper_payments=0),
    )
    report = audit(batch, cases, state, policy)
    metrics = batch.metrics.model_copy(update={"improper_payments": report.improper_payments})
    return batch.model_copy(update={"metrics": metrics}), report


# The agent's pass ------------------------------------------------------------------------------------------------


def _decide_agent(
    cases: Sequence[InvoiceCase], state: CompanyState, policy: Policy, vetoes: Mapping[str, str]
) -> tuple[list[Draft], defaultdict[tuple[int, int], Decimal]]:
    _ensure_unique_ids(cases)
    by_id = {case.id: case for case in cases}
    ordered = sorted(
        (read_facts(case, position, state.fx_units_per_base) for position, case in enumerate(cases)),
        key=lambda facts: facts.arrival,
    )
    matches = {f.case_id: match_beneficiary(policy, name=f.supplier_name, tax_id=f.supplier_tax_id) for f in ordered}
    suppliers = _suppliers(ordered, matches, state)
    spent_by_month = _agent_spending_in_history(state)
    balance, paid_ids, drafts = state.opening_balance, set[str](), list[Draft]()
    for facts in ordered:
        month = (facts.received_on.year, facts.received_on.month)
        context = RuleContext(
            invoice=facts,
            extraction=by_id[facts.case_id].extraction,
            policy=policy,
            fx=state.fx_units_per_base,
            match=matches[facts.case_id],
            earlier=_earlier(suppliers[_supplier_key(facts, matches)], facts, paid_ids),
            nearby=_nearby(suppliers[_supplier_key(facts, matches)], facts, policy, paid_ids),
            spent_auto=spent_by_month[month],
            balance=balance,
        )
        checks = tuple(EVALUATORS[spec.id](context) for spec in RULES)
        verdict = verdict_of(check.result for check in checks)
        veto = vetoes.get(facts.case_id) if verdict is AgentVerdict.PAY else None
        before = balance
        if veto is None and verdict is AgentVerdict.PAY and facts.amount_base is not None:
            balance -= facts.amount_base
            spent_by_month[month] += facts.amount_base
            paid_ids.add(facts.case_id)
        drafts.append(
            Draft(
                facts=facts,
                beneficiary=context.match.beneficiary,
                checks=checks,
                verdict=AgentVerdict.HOLD if veto else verdict,
                status=_agent_status(AgentVerdict.HOLD if veto else verdict),
                balance_before=before,
                balance_after=balance,
                spent_after=spent_by_month[month],
                blocked_reason=AUDITOR_VETO.format(finding=veto) if veto else None,
            )
        )
    return drafts, spent_by_month


def _ensure_unique_ids(cases: Sequence[InvoiceCase]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.id in seen:
            raise DuplicateCaseIdError(case.id)
        seen.add(case.id)


def _supplier_key(facts: InvoiceFacts, matches: Mapping[str, BeneficiaryMatch]) -> str:
    known = matches[facts.case_id].beneficiary
    if known is not None:
        return f"beneficiary:{known.id}"
    name = normalize_name(facts.supplier_name or "")
    return f"name:{name}" if name else f"case:{facts.case_id}"


def _suppliers(
    ordered: Sequence[InvoiceFacts], matches: Mapping[str, BeneficiaryMatch], state: CompanyState
) -> dict[str, _Supplier]:
    history: defaultdict[str, list[Charge]] = defaultdict(list)
    for record in state.history:
        if record.beneficiary_id is not None:
            history[f"beneficiary:{record.beneficiary_id}"].append(charge_from_history(record))
    invoices: defaultdict[str, list[InvoiceFacts]] = defaultdict(list)
    for facts in ordered:
        invoices[_supplier_key(facts, matches)].append(facts)
    return {key: _Supplier(tuple(history[key]), tuple(facts)) for key, facts in invoices.items()}


def _earlier(supplier: _Supplier, facts: InvoiceFacts, paid_ids: set[str]) -> tuple[Charge, ...]:
    earlier_invoices = (
        charge_from_invoice(other, paid=other.case_id in paid_ids)
        for other in supplier.invoices
        if other.arrival < facts.arrival
    )
    return (*supplier.history, *earlier_invoices)


def _nearby(supplier: _Supplier, facts: InvoiceFacts, policy: Policy, paid_ids: set[str]) -> tuple[Charge, ...]:
    def within(day: date) -> bool:
        return abs((facts.received_on - day).days) <= policy.split_window_days

    invoices = (
        charge_from_invoice(other, paid=other.case_id in paid_ids)
        for other in supplier.invoices
        if within(other.received_on)
    )
    return (*(charge for charge in supplier.history if within(charge.on)), *invoices)


def _agent_spending_in_history(state: CompanyState) -> defaultdict[tuple[int, int], Decimal]:
    spent: defaultdict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for record in state.history:
        if record.by == "agent":
            spent[(record.paid_on.year, record.paid_on.month)] += record.amount_base
    return spent


def _agent_status(verdict: AgentVerdict) -> DecisionStatus:
    return {
        AgentVerdict.PAY: DecisionStatus.PAID_AUTO,
        AgentVerdict.HOLD: DecisionStatus.HOLD,
        AgentVerdict.ESCALATE: DecisionStatus.PENDING_APPROVAL,
    }[verdict]


def _balance_after_agent(drafts: Sequence[Draft], state: CompanyState) -> Decimal:
    return drafts[-1].balance_after if drafts else state.opening_balance


# The people's approvals, applied after the batch at the moment they are given ---------------------------------


def _apply_approvals(
    drafts: list[Draft],
    approvals: Mapping[str, Approval],
    policy: Policy,
    vetoes: Mapping[str, str],
    balance: Decimal,
) -> tuple[list[Draft], Decimal]:
    index = {draft.facts.case_id: n for n, draft in enumerate(drafts)}
    in_order = sorted(
        ((invoice_id, given) for invoice_id, given in approvals.items() if invoice_id in index),
        key=lambda item: (as_utc(item[1].at), index[item[0]]),
    )
    result = list(drafts)
    for invoice_id, given in in_order:
        draft = result[index[invoice_id]]
        result[index[invoice_id]], balance = _apply_one(draft, given, policy, vetoes.get(invoice_id), balance)
    return result, balance


def _apply_one(
    draft: Draft, given: Approval, policy: Policy, veto: str | None, balance: Decimal
) -> tuple[Draft, Decimal]:
    if draft.verdict is AgentVerdict.PAY:
        return draft, balance
    if draft.verdict is AgentVerdict.HOLD:
        note = draft.blocked_reason or (_hold_rule_note(draft) if given.decision == "approved" else None)
        return replace(draft, approval=given, blocked_reason=note), balance
    if given.decision == "rejected":
        return replace(draft, approval=given, status=DecisionStatus.REJECTED), balance
    return _pay_approved(draft, given, policy, veto, balance)


def _pay_approved(
    draft: Draft, given: Approval, policy: Policy, veto: str | None, balance: Decimal
) -> tuple[Draft, Decimal]:
    amount_base, base = draft.facts.amount_base, policy.base_currency
    if amount_base is None:
        return _blocked(draft, given, NO_BASE_AMOUNT.format(base=base)), balance
    if veto is not None:
        return _blocked(draft, given, AUDITOR_VETO.format(finding=veto)), balance
    shortfall = balance_below_reserve(balance, amount_base, policy)
    if shortfall is not None:
        note = RESERVE_BREACH.format(after=money(shortfall, base), reserve=money(policy.reserve, base))
        return _blocked(draft, given, note), balance
    after = balance - amount_base
    paid = replace(draft, approval=given, status=DecisionStatus.PAID_HUMAN, balance_before=balance, balance_after=after)
    return paid, after


def _blocked(draft: Draft, given: Approval, reason: str) -> Draft:
    return replace(draft, approval=given, status=DecisionStatus.HOLD, blocked_reason=reason)


def _hold_rule_note(draft: Draft) -> str:
    labels = [check.result.label for check in draft.checks if check.result.outcome is RuleOutcome.HOLD]
    return HOLD_RULE_APPROVED.format(labels=", ".join(labels))


def _finish(draft: Draft) -> Decision:
    facts = draft.facts
    return Decision(
        invoice_id=facts.case_id,
        beneficiary_id=draft.beneficiary.id if draft.beneficiary else None,
        supplier_name=draft.beneficiary.name if draft.beneficiary else facts.supplier_name,
        amount=facts.amount,
        currency=facts.currency,
        amount_base=facts.amount_base,
        agent_verdict=draft.verdict,
        status=draft.status,
        rules=[check.result for check in draft.checks],
        explanation=explanation(draft),
        counterfactual=counterfactual(draft),
        balance_before=draft.balance_before,
        balance_after=draft.balance_after,
        approval=draft.approval,
        blocked_reason=draft.blocked_reason,
    )
