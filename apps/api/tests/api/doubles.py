"""Test doubles behind the public signatures of lanes L1, L2 and L3.

They are small but honest: the fake reader parses labelled Spanish text, the fake engine applies a handful of the
real rules (unread, injection, beneficiary, account, duplicate, currency, approval threshold, reserve) and the fake
ledger follows the hashing spec in docs/DESIGN.md §5. The API only ever sees the contract types.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from custodio.contracts import (
    RULES,
    AgentVerdict,
    Approval,
    Approver,
    AttackSpec,
    AuditFinding,
    AuditReport,
    BatchResult,
    Beneficiary,
    CompanyProfile,
    CompanyState,
    Decision,
    DecisionStatus,
    Evidence,
    ExtractedField,
    ExtractedInvoice,
    HiddenTextFinding,
    HiddenTextKind,
    InvoiceCase,
    InvoiceSource,
    InvoiceSpec,
    LedgerEntry,
    LedgerKind,
    LedgerVerification,
    Metrics,
    Policy,
    PolicyChange,
    PolicyProposal,
    RedTeamEvent,
    RenderedDocument,
    RuleOutcome,
    RuleResult,
    SimulatedChange,
    SimulationReport,
    SupplierImport,
)
from custodio.llm import LLMError
from custodio.services.lanes import Lanes
from custodio.services.notifier import ApprovalRequest
from custodio.services.triage import AttackTriage

GENESIS = "0" * 64
TODAY = date(2026, 10, 17)

NUBE = Beneficiary(
    id="B-NUBE",
    name="Nube Hosting S.A.S.",
    tax_id="900123456",
    bank_name="Banco Andino",
    account_number="111222333",
    currency="USD",
)
ARRIENDO = Beneficiary(
    id="B-ARRIENDO",
    name="Inmobiliaria Prado",
    tax_id="800555444",
    bank_name="Banco Andino",
    account_number="555666777",
    currency="USD",
)

LABELS = {
    "proveedor": "supplier_name",
    "identificación tributaria": "supplier_tax_id",
    "número de factura": "invoice_number",
    "fecha de emisión": "issue_date",
    "monto": "amount",
    "moneda": "currency",
    "banco": "bank_name",
    "cuenta": "account_number",
    "concepto": "description",
}
INJECTION_MARKERS = ("ignora", "ignore previous", "aprueba esta factura")


def invoice_text(
    *,
    supplier: str = NUBE.name,
    tax_id: str = NUBE.tax_id,
    number: str = "FV-100",
    amount: str = "1200.00",
    currency: str = "USD",
    account: str = NUBE.account_number,
    note: str = "",
) -> str:
    lines = [
        f"Proveedor: {supplier}",
        f"Identificación tributaria: {tax_id}",
        f"Número de factura: {number}",
        "Fecha de emisión: 2026-10-15",
        f"Monto: {amount}",
        f"Moneda: {currency}",
        "Banco: Banco Andino",
        f"Cuenta: {account}",
        "Concepto: Servicio mensual",
    ]
    return "\n".join([*lines, note]).strip()


# ---------------------------------------------------------------------------
# L1 · dataset
# ---------------------------------------------------------------------------


def demo_company() -> tuple[CompanyState, Policy]:
    state = CompanyState(
        workspace_id="demo",
        company_name="Cobalto Labs, Inc.",
        today=TODAY,
        opening_balance=Decimal("100000"),
        fx_units_per_base={"USD": Decimal("1"), "COP": Decimal("4000")},
    )
    policy = Policy(
        beneficiaries=[NUBE, ARRIENDO],
        approvers=[Approver(name="Ana Gómez", role="Gerente financiera", telegram_chat_id="4242")],
    )
    return state, policy


def demo_cases() -> list[InvoiceCase]:
    specs = [
        ("F01", invoice_text(number="FV-001", amount="1200.00"), "pay", None),
        ("F02", invoice_text(number="FV-002", amount="7000.00"), "escalate", "sobre el tope de aprobación"),
        ("F03", invoice_text(number="FV-003", account="999000111"), "hold", "cuenta cambiada"),
    ]
    return [
        InvoiceCase(
            id=case_id,
            received_at=datetime(2026, 10, 10 + index, 9, 0, tzinfo=UTC),
            extraction=extract_text(text, document_id=f"doc-{case_id}"),
            expected=expected,
            trap=trap,
        )
        for index, (case_id, text, expected, trap) in enumerate(specs)
    ]


def demo_specs() -> list[InvoiceSpec]:
    return []


# ---------------------------------------------------------------------------
# L2 · reading
# ---------------------------------------------------------------------------


def _field(value: str | None) -> ExtractedField:
    if value is None:
        return ExtractedField(value=None, confidence=0.0, verified=False)
    return ExtractedField(value=value, evidence=Evidence(quote=value), confidence=1.0, verified=True)


def _parse_labels(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        label, _, value = line.partition(":")
        key = LABELS.get(label.strip().lower())
        if key and value.strip():
            values.setdefault(key, value.strip())
    return values


def _findings(text: str) -> list[HiddenTextFinding]:
    lowered = text.lower()
    if any(marker in lowered for marker in INJECTION_MARKERS):
        return [HiddenTextFinding(kind=HiddenTextKind.INSTRUCTION, text=text[:80], detail="Instrucción al agente.")]
    return []


def extract_text(text: str, *, document_id: str, source: InvoiceSource = InvoiceSource.TEXT) -> ExtractedInvoice:
    values = _parse_labels(text)
    fields = {name: _field(values.get(name)) for name in LABELS.values()}
    return ExtractedInvoice(
        document_id=document_id,
        source=source,
        visible_text=text,
        hidden_findings=_findings(text),
        reader="fake-reader",
        overall_confidence=1.0 if values else 0.0,
        due_date=_field(None),
        **fields,
    )


def extract_document(data: bytes, *, filename: str, media_type: str, document_id: str) -> ExtractedInvoice:
    source = InvoiceSource.PDF if media_type == "application/pdf" else InvoiceSource.IMAGE
    return extract_text(data.decode("utf-8", errors="replace"), document_id=document_id, source=source)


def render_invoice(spec: InvoiceSpec) -> RenderedDocument:
    text = invoice_text(
        supplier=spec.supplier_name,
        tax_id=spec.supplier_tax_id,
        number=spec.invoice_number,
        amount=str(spec.amount),
        currency=spec.currency,
        account=spec.account_number,
    )
    return RenderedDocument(filename=f"{spec.invoice_number}.txt", media_type="text/plain", data=text.encode())


# ---------------------------------------------------------------------------
# L1 · engine
# ---------------------------------------------------------------------------


@dataclass
class _Facts:
    beneficiary: Beneficiary | None
    amount: Decimal | None
    currency: str | None
    amount_base: Decimal | None
    number: str | None


def _facts(case: InvoiceCase, state: CompanyState, policy: Policy) -> _Facts:
    reading = case.extraction
    tax_id = reading.supplier_tax_id.value
    beneficiary = next((b for b in policy.beneficiaries if b.tax_id == tax_id and b.allowed), None)
    amount = Decimal(reading.amount.value) if reading.amount.value else None
    currency = reading.currency.value
    fx = state.fx_units_per_base.get(currency or "")
    amount_base = (amount / fx).quantize(Decimal("0.01")) if amount is not None and fx else None
    return _Facts(beneficiary, amount, currency, amount_base, reading.invoice_number.value)


def _failures(case: InvoiceCase, facts: _Facts, policy: Policy, balance: Decimal, seen: set[str]) -> dict[str, str]:
    reading = case.extraction
    failures: dict[str, str] = {}
    if facts.amount is None or not reading.amount.verified or facts.amount_base is None:
        failures["R1"] = "No se pudo leer el monto con evidencia verificada."
    if reading.hidden_findings:
        failures["R2"] = "El documento trae instrucciones dirigidas al agente."
    if facts.beneficiary is None:
        failures["R3"] = "El proveedor no está entre los beneficiarios permitidos."
    elif reading.account_number.value != facts.beneficiary.account_number:
        failures["R4"] = "La cuenta leída no es la registrada."
    if facts.number and facts.number in seen:
        failures["R5"] = f"La factura {facts.number} ya se había recibido."
    if facts.currency is not None and facts.currency not in policy.allowed_currencies:
        failures["R8"] = f"La moneda {facts.currency} no está permitida."
    if facts.amount_base is not None and facts.amount_base > policy.approval_threshold:
        failures["R9"] = f"USD {facts.amount_base} supera el tope de {policy.approval_threshold}."
    if facts.amount_base is not None and balance - facts.amount_base < policy.reserve:
        failures["R12"] = "Pagar dejaría el saldo bajo la reserva."
    return failures


def _rules(failures: Mapping[str, str]) -> list[RuleResult]:
    return [
        RuleResult(
            rule_id=spec.id,
            key=spec.key,
            label=spec.label,
            outcome=RuleOutcome(spec.effect.value) if spec.id in failures else RuleOutcome.PASS,
            reason=failures.get(spec.id, "Cumple."),
        )
        for spec in RULES
    ]


def _verdict(failures: Mapping[str, str]) -> AgentVerdict:
    rules = {rule.id: rule for rule in RULES}
    effects = {rules[rule_id].effect.value for rule_id in failures}
    if "hold" in effects:
        return AgentVerdict.HOLD
    return AgentVerdict.ESCALATE if effects else AgentVerdict.PAY


STATUS_BY_VERDICT = {
    AgentVerdict.PAY: DecisionStatus.PAID_AUTO,
    AgentVerdict.HOLD: DecisionStatus.HOLD,
    AgentVerdict.ESCALATE: DecisionStatus.PENDING_APPROVAL,
}


def _decide_one(case: InvoiceCase, state: CompanyState, policy: Policy, balance: Decimal, seen: set[str]) -> Decision:
    facts = _facts(case, state, policy)
    failures = _failures(case, facts, policy, balance, seen)
    verdict = _verdict(failures)
    paid = verdict is AgentVerdict.PAY and facts.amount_base is not None
    return Decision(
        invoice_id=case.id,
        beneficiary_id=facts.beneficiary.id if facts.beneficiary else None,
        supplier_name=case.extraction.supplier_name.value,
        amount=facts.amount,
        currency=facts.currency,
        amount_base=facts.amount_base,
        agent_verdict=verdict,
        status=STATUS_BY_VERDICT[verdict],
        rules=_rules(failures),
        explanation="Se pagó." if paid else "; ".join(failures.values()),
        counterfactual=None if paid else "Se habría pagado si todas las reglas se cumplieran.",
        balance_before=balance,
        balance_after=balance - facts.amount_base if paid and facts.amount_base is not None else balance,
    )


def _apply_approval(decision: Decision, approval: Approval, balance: Decimal, policy: Policy) -> Decision:
    if decision.status is not DecisionStatus.PENDING_APPROVAL:
        return decision
    if approval.decision == "rejected":
        return decision.model_copy(update={"status": DecisionStatus.REJECTED, "approval": approval})
    amount = decision.amount_base or Decimal(0)
    if balance - amount < policy.reserve:
        return decision.model_copy(
            update={
                "status": DecisionStatus.HOLD,
                "approval": approval,
                "blocked_reason": "Aprobada, pero pagarla rompería la reserva.",
            }
        )
    return decision.model_copy(
        update={
            "status": DecisionStatus.PAID_HUMAN,
            "approval": approval,
            "balance_before": balance,
            "balance_after": balance - amount,
        }
    )


def _metrics(decisions: Sequence[Decision], cases: Sequence[InvoiceCase]) -> Metrics:
    def count(status: DecisionStatus) -> int:
        return sum(1 for d in decisions if d.status is status)

    total = len(decisions)
    autonomous = count(DecisionStatus.PAID_AUTO) + count(DecisionStatus.HOLD)
    return Metrics(
        total=total,
        paid_auto=count(DecisionStatus.PAID_AUTO),
        paid_human=count(DecisionStatus.PAID_HUMAN),
        hold=count(DecisionStatus.HOLD),
        pending=count(DecisionStatus.PENDING_APPROVAL),
        rejected=count(DecisionStatus.REJECTED),
        autonomy_rate=autonomous / total if total else 0.0,
        improper_payments=0,
    )


def decide_all(
    cases: Sequence[InvoiceCase],
    state: CompanyState,
    policy: Policy,
    approvals: Mapping[str, Approval] | None = None,
) -> BatchResult:
    assert all(case.expected is None and case.trap is None for case in cases), "the engine never sees labels"
    balance = state.opening_balance
    seen = {record.invoice_number for record in state.history if record.invoice_number}
    decisions: list[Decision] = []
    for case in sorted(cases, key=lambda c: c.received_at):
        decision = _decide_one(case, state, policy, balance, seen)
        balance = decision.balance_after if decision.balance_after is not None else balance
        if decision.amount is not None and case.extraction.invoice_number.value:
            seen.add(case.extraction.invoice_number.value)
        decisions.append(decision)
    for index, decision in enumerate(decisions):
        approval = (approvals or {}).get(decision.invoice_id)
        if approval is not None:
            decisions[index] = _apply_approval(decision, approval, balance, policy)
            if decisions[index].status is DecisionStatus.PAID_HUMAN:
                balance -= decisions[index].amount_base or Decimal(0)
    return BatchResult(
        decisions=decisions,
        spent_auto_base=sum(
            (d.amount_base or Decimal(0) for d in decisions if d.status is DecisionStatus.PAID_AUTO), Decimal(0)
        ),
        balance_end=balance,
        metrics=_metrics(decisions, cases),
    )


@dataclass
class FakeAuditor:
    """Agrees with the engine unless told to flag specific invoices as improper payments."""

    flagged: set[str] = field(default_factory=set)

    def __call__(
        self, batch: BatchResult, cases: Sequence[InvoiceCase], state: CompanyState, policy: Policy
    ) -> AuditReport:
        paid = [d for d in batch.decisions if d.status in {DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN}]
        findings = [
            AuditFinding(invoice_id=d.invoice_id, severity="critical", message="El auditor no reconoce este pago.")
            for d in paid
            if d.invoice_id in self.flagged
        ]
        return AuditReport(agrees=not findings, checked=len(paid), improper_payments=len(findings), findings=findings)


def simulate(cases: Sequence[InvoiceCase], state: CompanyState, before: Policy, after: Policy) -> SimulationReport:
    old = decide_all(cases, state, before)
    new = decide_all(cases, state, after)
    changed = [
        SimulatedChange(
            invoice_id=a.invoice_id,
            supplier_name=a.supplier_name,
            before=a.status,
            after=b.status,
            reason=b.explanation,
        )
        for a, b in zip(old.decisions, new.decisions, strict=True)
        if a.status is not b.status
    ]
    return SimulationReport(before=old.metrics, after=new.metrics, changed=changed)


def _canonical(value: Any) -> str:
    def default(obj: Any) -> str:
        if isinstance(obj, Decimal):
            return str(obj.normalize())
        if isinstance(obj, datetime):
            return obj.astimezone(UTC).isoformat()
        raise TypeError(type(obj))

    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=default, ensure_ascii=False)


def _hash(
    prev_hash: str, seq: int, at: datetime, kind: LedgerKind, subject_id: str | None, payload: dict[str, Any]
) -> str:
    body = {"seq": seq, "at": at, "kind": kind.value, "subject_id": subject_id, "payload": payload}
    return hashlib.sha256((prev_hash + _canonical(body)).encode()).hexdigest()


def next_entry(
    prev: LedgerEntry | None, *, kind: LedgerKind, subject_id: str | None, payload: dict[str, Any], at: datetime
) -> LedgerEntry:
    seq = prev.seq + 1 if prev else 1
    prev_hash = prev.hash if prev else GENESIS
    digest = _hash(prev_hash, seq, at, kind, subject_id, payload)
    return LedgerEntry(
        seq=seq, at=at, kind=kind, subject_id=subject_id, payload=payload, prev_hash=prev_hash, hash=digest
    )


def verify(entries: Sequence[LedgerEntry]) -> LedgerVerification:
    prev_hash = GENESIS
    for entry in entries:
        expected = _hash(prev_hash, entry.seq, entry.at, entry.kind, entry.subject_id, entry.payload)
        if entry.prev_hash != prev_hash or entry.hash != expected:
            return LedgerVerification(valid=False, length=len(entries), first_broken_seq=entry.seq, head_hash=None)
        prev_hash = entry.hash
    head = entries[-1].hash if entries else None
    return LedgerVerification(valid=True, length=len(entries), first_broken_seq=None, head_hash=head)


# ---------------------------------------------------------------------------
# L3 · AI features
# ---------------------------------------------------------------------------


def compile_policy(text: str, current: Policy) -> PolicyProposal:
    numbers = [token.replace(".", "") for token in text.split() if token.replace(".", "").isdigit()]
    if not numbers:
        return PolicyProposal(text=text, changes=[], unsupported=[text], proposed=current)
    threshold = Decimal(numbers[0])
    change = PolicyChange(
        field="approval_threshold",
        label="Tope de aprobación automática",
        before=float(current.approval_threshold),
        after=float(threshold),
        source_quote=text,
    )
    proposed = current.model_copy(update={"approval_threshold": threshold})
    return PolicyProposal(text=text, changes=[change], unsupported=[], proposed=proposed)


def narrate(decision: Decision) -> str:
    return f"En palabras simples: {decision.explanation}"


def profile_company(company_name: str, website: str | None, answers: Mapping[str, str]) -> CompanyProfile:
    return CompanyProfile(
        company_name=company_name,
        website=website,
        industry=answers.get("industria"),
        summary=f"{company_name} es una empresa de prueba.",
        evidence_urls=[website] if website else [],
    )


def import_suppliers(data: bytes, *, filename: str, media_type: str) -> SupplierImport:
    beneficiaries: list[Beneficiary] = []
    warnings: list[str] = []
    for number, row in enumerate(data.decode().splitlines(), start=1):
        cells = [cell.strip() for cell in row.split(",")]
        if len(cells) != 4:
            warnings.append(f"Fila {number}: incompleta.")
            continue
        name, tax_id, bank, account = cells
        beneficiaries.append(
            Beneficiary(
                id=f"B-{tax_id}", name=name, tax_id=tax_id, bank_name=bank, account_number=account, currency="USD"
            )
        )
    return SupplierImport(beneficiaries=beneficiaries, warnings=warnings)


def attack(round_number: int) -> AttackSpec:
    """Each round changes the account of a trusted supplier: the engine must hold it."""
    return AttackSpec(
        round=round_number,
        technique="Cuenta cambiada",
        rationale="La cuenta nueva parece legítima.",
        target_rules=["R4"],
        render_as="text",
        invoice_text=invoice_text(number=f"RT-{round_number}", account=f"7770{round_number}"),
    )


def red_team(
    policy: Policy, state: CompanyState, *, rounds: int, judge: Callable[[AttackSpec], Decision]
) -> Iterator[RedTeamEvent]:
    caught_total = 0
    for round_number in range(1, rounds + 1):
        yield RedTeamEvent(type="round_started", round=round_number)
        spec = attack(round_number)
        yield RedTeamEvent(type="attack_generated", round=round_number, attack=spec)
        decision = judge(spec)
        caught = decision.status not in {DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN}
        caught_total += caught
        yield RedTeamEvent(type="verdict", round=round_number, attack=spec, decision=decision, caught=caught)
        yield RedTeamEvent(type="round_finished", round=round_number)
    yield RedTeamEvent(type="summary", round=rounds, message=f"{caught_total} de {rounds} ataques atrapados.")


def triage_attack(text: str) -> AttackTriage:
    return AttackTriage(technique="Cuenta cambiada" if "Cuenta" in text else "Otra", creativity=7)


def failing(*_: object, **__: object) -> Any:
    raise LLMError("El modelo no respondió.")


def fake_lanes(auditor: FakeAuditor | None = None) -> Lanes:
    return Lanes(
        demo_company=demo_company,
        demo_cases=demo_cases,
        extract_document=extract_document,
        extract_text=extract_text,
        render_invoice=render_invoice,
        decide_all=decide_all,
        audit=auditor or FakeAuditor(),
        simulate=simulate,
        next_ledger_entry=next_entry,
        verify_ledger=verify,
        compile_policy=compile_policy,
        narrate=narrate,
        profile_company=profile_company,
        import_suppliers=import_suppliers,
        red_team=red_team,
        triage_attack=triage_attack,
    )


@dataclass
class RecordingNotifier:
    """Keeps every Telegram message instead of sending it."""

    requests: list[ApprovalRequest] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)

    def send_approval_request(self, request: ApprovalRequest) -> None:
        self.requests.append(request)

    def answer_callback(self, callback_id: str, text: str) -> None:
        self.answers.append(text)
