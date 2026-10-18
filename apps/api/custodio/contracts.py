"""Shared contracts between every part of Custodio.

These models are the seams between lanes (engine, extraction, AI, API, web). Changing a field here is a
contract change: it needs the coordinator's approval and a note in docs/DESIGN.md.

Money is Decimal in Python and a JSON number on the wire. Product text (labels, reasons, explanations) is
Spanish; identifiers and code are English.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

Amount = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Ratio = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Rules catalogue (fixed ids; the engine evaluates all fifteen, in this order)
# ---------------------------------------------------------------------------


class RuleEffect(StrEnum):
    HOLD = "hold"  # the agent stops the payment on its own (no person needed)
    ESCALATE = "escalate"  # the agent asks a person


class RuleSpec(Model):
    id: str
    key: str
    label: str
    effect: RuleEffect
    # True for the payment controls R13-R15: their SKIPPED means there was nothing to check (no account scheme with a
    # public check digit, no name, no registered domain) and does not stop a payment that R1-R12 allow.
    neutral_when_skipped: bool = False


RULES: tuple[RuleSpec, ...] = (
    RuleSpec(id="R1", key="reading", label="Lectura confiable", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R2", key="injection", label="Sin instrucciones escondidas", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R3", key="beneficiary", label="Beneficiario permitido", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R4", key="account", label="Cuenta registrada", effect=RuleEffect.HOLD),
    RuleSpec(id="R5", key="duplicate", label="Sin cobro duplicado", effect=RuleEffect.HOLD),
    RuleSpec(id="R6", key="agreement", label="Coincide con lo acordado", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R7", key="split", label="Sin pagos fraccionados", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R8", key="currency", label="Moneda permitida", effect=RuleEffect.HOLD),
    RuleSpec(id="R9", key="approval", label="Tope de aprobación automática", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R10", key="limit", label="Límite por pago", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R11", key="budget", label="Cupo de pago automático", effect=RuleEffect.ESCALATE),
    RuleSpec(id="R12", key="reserve", label="Saldo y reserva", effect=RuleEffect.HOLD),
    RuleSpec(
        id="R13",
        key="bank_details",
        label="Datos bancarios válidos para el riel",
        effect=RuleEffect.ESCALATE,
        neutral_when_skipped=True,
    ),
    RuleSpec(
        id="R14",
        key="sanctions",
        label="Sin coincidencia en la lista OFAC",
        effect=RuleEffect.ESCALATE,
        neutral_when_skipped=True,
    ),
    RuleSpec(
        id="R15",
        key="out_of_band",
        label="Verificación fuera de banda",
        effect=RuleEffect.ESCALATE,
        neutral_when_skipped=True,
    ),
)


# ---------------------------------------------------------------------------
# Company configuration: beneficiaries, agreements and policy
# ---------------------------------------------------------------------------


class AgreementKind(StrEnum):
    FIXED = "fixed"  # every invoice must match `amount` within tolerance
    MONTHLY_CAP = "monthly_cap"  # the sum of the month's invoices must not exceed `amount`


class EarlyPaymentDiscount(Model):
    """Early-payment terms such as "2/10 net 30": `percent` off when paid within `days` of the issue date."""

    percent: Ratio
    days: int = Field(ge=0)


class Agreement(Model):
    kind: AgreementKind
    amount: Amount
    currency: str
    tolerance_pct: Ratio | None = None  # overrides Policy.agreement_tolerance_pct when set
    source: str | None = None  # where it came from, e.g. "Contrato marco 2026, cláusula 4"
    early_payment_discount: EarlyPaymentDiscount | None = None  # the scheduler pays early only to earn it
    late_fee_pct: Ratio | None = None  # agreed late fee per month overdue; ranks payments when cash is short
    critical: bool = False  # e.g. payroll or rent: paid first when cash is short, after late fees


class Beneficiary(Model):
    id: str
    name: str
    tax_id: str
    aliases: list[str] = []
    country: str | None = None  # ISO 3166-1 alpha-2
    bank_name: str
    account_number: str  # demo data only; a real deployment stores a fingerprint, never the number
    currency: str  # ISO 4217
    agreement: Agreement | None = None
    allowed: bool = True  # False = blocked beneficiary (R3 escalates)
    approver_contact: str | None = None  # the known phone or email R15 tells a person to verify a change with
    email_domain: str | None = None  # e.g. "andescode.co"; R15 compares it with the sender's


class Approver(Model):
    name: str
    role: str | None = None
    email: str | None = None


class TrustPolicy(Model):
    """How a supplier earns a higher auto-approval cap (R9). See custodio.engine.trust for the formula."""

    floor: Amount = Decimal(0)  # the cap of a supervised supplier, after any risk signal
    hard_ceiling: bool = False  # True: an earned cap never exceeds approval_threshold; else per_payment_limit


class Policy(Model):
    """Everything a company decides. Amount thresholds are expressed in `base_currency`."""

    version: int = 1
    base_currency: str = "USD"
    approval_threshold: Amount = Decimal("5000")  # R9: above this, a person approves
    per_payment_limit: Amount = Decimal("12000")  # R10: no single payment above this without a person
    period_budget: Amount = Decimal("37000")  # R11: the agent's autonomous cupo per calendar month
    reserve: Amount = Decimal("60000")  # R12: balance that is never touched
    agreement_tolerance_pct: Ratio = Decimal("2")  # R6
    duplicate_window_days: int = 20  # R5
    split_window_days: int = 2  # R7
    min_confidence: Ratio = Decimal("0.9")  # R1
    allowed_currencies: list[str] = ["USD", "COP", "MXN", "BRL", "CLP"]  # R8
    beneficiaries: list[Beneficiary] = []  # R3, R4, R6
    approvers: list[Approver] = []
    trust: TrustPolicy = TrustPolicy()  # R9 per supplier, earned in the ledger


class PaymentRecord(Model):
    """A payment already made (or approved) before the current batch; used by R5, R7 and R11."""

    invoice_id: str
    beneficiary_id: str | None
    invoice_number: str | None
    amount: Amount
    currency: str
    amount_base: Amount
    paid_on: date
    by: Literal["agent", "person"]


class TrustCap(Model):
    """The auto-approval cap (R9) one supplier has earned, folded from its trust entries in the ledger."""

    beneficiary_id: str
    cap: Amount  # in base currency
    clean_streak: int  # payments a person approved without an incident since the last one
    supervised: bool  # True after a risk signal, until the supplier earns its cap back
    reason: str  # Spanish, why the cap is what it is


class CompanyState(Model):
    workspace_id: str
    company_name: str
    today: date
    opening_balance: Amount  # in base currency, before the batch
    fx_units_per_base: dict[str, Ratio]  # units of each currency per 1 unit of base currency
    history: list[PaymentRecord] = []
    trust: dict[str, TrustCap] = {}  # by beneficiary id; a supplier without one uses Policy.approval_threshold


# ---------------------------------------------------------------------------
# Reading invoices
# ---------------------------------------------------------------------------


class Evidence(Model):
    quote: str  # exact text from the source document that supports the value
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None


class ExtractedField(Model):
    value: str | None  # normalized: dates ISO-8601, amounts "12500.00", currency ISO 4217
    evidence: Evidence | None = None
    confidence: float = Field(ge=0, le=1)
    verified: bool = False  # set by code, never by a model: the quote exists in the source and supports value


class HiddenTextKind(StrEnum):
    INVISIBLE_COLOR = "invisible_color"  # text drawn in the background color
    TINY_FONT = "tiny_font"
    OFF_PAGE = "off_page"
    COVERED = "covered"  # text under an image or a filled shape
    METADATA = "metadata"  # instructions in document metadata or annotations
    INSTRUCTION = "instruction"  # visible or not, text addressed to an AI agent


class HiddenTextFinding(Model):
    kind: HiddenTextKind
    text: str
    page: int | None = None
    detail: str  # Spanish, for the acta


class InvoiceSource(StrEnum):
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    INTENT = "intent"  # a payment intent submitted by another agent through the firewall


class CrossCheckStatus(StrEnum):
    AGREE = "agree"  # every reader gave the same normalized value for every compared field
    DISAGREE = "disagree"
    UNAVAILABLE = "unavailable"  # the second reading failed, timed out or had no budget: fail closed


class ReaderValue(Model):
    reader: str  # e.g. "claude-sonnet-5-5", "gemini-2.5-flash", "etiquetas"
    value: str | None  # normalized like ExtractedField.value; None when that reader did not state it
    quote: str | None = None


class FieldCrossCheck(Model):
    field: Literal["supplier_name", "amount", "currency", "account_number"]
    readings: list[ReaderValue]
    agree: bool


class ReadingCrossCheck(Model):
    """Two independent readings of the same document, compared field by field by code (R1 and the auditor)."""

    status: CrossCheckStatus
    fields: list[FieldCrossCheck] = []
    error: str | None = None  # why the second reading is missing, in Spanish


class ExtractedInvoice(Model):
    document_id: str
    source: InvoiceSource
    supplier_name: ExtractedField
    supplier_tax_id: ExtractedField
    invoice_number: ExtractedField
    issue_date: ExtractedField
    due_date: ExtractedField
    amount: ExtractedField
    currency: ExtractedField
    bank_name: ExtractedField
    account_number: ExtractedField
    description: ExtractedField
    visible_text: str
    sender_email: str | None = None  # first email address in the document, found by code (R15)
    hidden_findings: list[HiddenTextFinding] = []
    reader: str  # pipeline that produced it, e.g. "pdfplumber+claude-sonnet-5-5"
    overall_confidence: float = Field(ge=0, le=1)
    cross_check: ReadingCrossCheck | None = None  # None: read without a model (labels), no second reading to compare


class InvoiceSpec(Model):
    """What an invoice says, before it becomes a document. The dataset, the renderer and the red team share it."""

    supplier_name: str
    supplier_tax_id: str
    tax_label: str = "NIT"
    invoice_number: str
    issue_date: date
    due_date: date | None = None
    amount: Amount
    currency: str
    amount_text: str | None = None  # how the amount is written, e.g. "$ 4.200.000" (ambiguous currency trap)
    bank_name: str
    account_number: str
    description: str
    channel: InvoiceSource = InvoiceSource.PDF
    note: str | None = None  # extra visible text (greeting, payment instructions, visible injection)
    hidden_text: str | None = None  # rendered invisibly (white text, tiny font, metadata)


class RenderedDocument(Model):
    filename: str
    media_type: str
    data: bytes


class InvoiceCase(Model):
    """One invoice entering the decision engine."""

    id: str
    received_at: datetime
    extraction: ExtractedInvoice
    expected: Literal["pay", "hold", "escalate"] | None = None  # dataset ground truth; the engine never reads it
    trap: str | None = None  # dataset label; the engine never reads it


# ---------------------------------------------------------------------------
# Decisions, audit and ledger
# ---------------------------------------------------------------------------


class RuleOutcome(StrEnum):
    PASS = "pass"
    HOLD = "hold"
    ESCALATE = "escalate"
    SKIPPED = "skipped"  # could not be evaluated because an earlier fact is missing (stated in reason)


class RuleResult(Model):
    rule_id: str
    key: str
    label: str
    outcome: RuleOutcome
    reason: str  # Spanish, one sentence, with the concrete numbers
    facts: dict[str, Any] = {}


class AgentVerdict(StrEnum):
    PAY = "pay"
    HOLD = "hold"
    ESCALATE = "escalate"


class DecisionStatus(StrEnum):
    PAID_AUTO = "paid_auto"
    PAID_HUMAN = "paid_human"
    HOLD = "hold"
    PENDING_APPROVAL = "pending_approval"
    REJECTED = "rejected"


class Approval(Model):
    invoice_id: str
    decision: Literal["approved", "rejected"]
    approver: str
    channel: Literal["web", "api"]
    at: datetime
    note: str | None = None


PaymentNetwork = Literal["ach", "wire", "bre_b", "spei", "pix"]


class PaymentInstruction(Model):
    """Exactly what Custodio hands a bank partner (Blinka) to pay one invoice: original amount and currency."""

    network: PaymentNetwork
    amount: Amount
    currency: str  # ISO 4217, as invoiced
    beneficiary_name: str
    beneficiary_tax_id: str
    beneficiary_country: str | None
    bank_name: str
    account_number: str
    reference: str  # the acta URL, so whoever reads the bank statement can see why it was paid
    idempotency_key: str


class PaymentExecution(Model):
    """What the payment rail did with a payment the engine decided. The rail executes; it never decides."""

    rail: Literal["simulated", "stripe_test", "blinka_simulated"]
    status: Literal["executed", "simulated", "failed"]
    external_id: str | None = None  # e.g. the Stripe transfer id
    dashboard_url: str | None = None
    executed_at: datetime
    error: str | None = None  # Spanish, never a secret
    instruction: PaymentInstruction | None = None  # set by rails that hand the payment to a bank partner


class Decision(Model):
    invoice_id: str
    beneficiary_id: str | None
    supplier_name: str | None
    amount: Amount | None
    currency: str | None
    amount_base: Amount | None
    agent_verdict: AgentVerdict
    status: DecisionStatus
    rules: list[RuleResult]  # always the fifteen rules, in catalogue order
    explanation: str  # deterministic Spanish text built by the engine from the rule results
    counterfactual: str | None  # "Se habría pagado si …"; None when it was paid
    narrative: str | None = None  # optional model-written plain-language version; every number is checked
    balance_before: Amount | None = None
    balance_after: Amount | None = None
    approval: Approval | None = None
    blocked_reason: str | None = None  # e.g. approved by a person but paying would break the reserve
    execution: PaymentExecution | None = None  # set only where money is meant to move: the panel, never a sandbox
    trust: TrustCap | None = None  # the supplier's earned R9 cap, when one replaced the policy's threshold


class Metrics(Model):
    total: int
    paid_auto: int
    paid_human: int
    hold: int
    pending: int
    rejected: int
    autonomy_rate: float  # (paid_auto + hold) / total: decided without a person
    accuracy: float | None = None  # agreement with InvoiceCase.expected when the dataset has labels
    improper_payments: int  # payments the independent auditor rejects; must always be 0


class BatchResult(Model):
    decisions: list[Decision]
    spent_auto_base: Amount  # autonomous spend this period, including history
    balance_end: Amount
    metrics: Metrics


class AuditFinding(Model):
    invoice_id: str
    severity: Literal["critical", "warning"]
    message: str


class AuditReport(Model):
    agrees: bool
    checked: int
    improper_payments: int
    findings: list[AuditFinding] = []


class LedgerKind(StrEnum):
    POLICY_CHANGED = "policy_changed"
    INVOICE_RECEIVED = "invoice_received"
    DECISION = "decision"
    APPROVAL = "approval"
    PAYMENT = "payment"
    REDTEAM_ATTACK = "redteam_attack"
    CHALLENGE_ATTEMPT = "challenge_attempt"
    INTENT = "intent"
    TRUST_RAISED = "trust_raised"  # a payment a person approved without an incident: the supplier earns trust
    TRUST_REVOKED = "trust_revoked"  # a risk signal of the supplier: back to supervised
    SIMULATION = "simulation"  # the demo's simulated month, with the cash it adds
    RECONCILIATION = "reconciliation"  # a statement reconciled, and each payment the bank confirmed
    RECONCILIATION_REVIEW = "reconciliation_review"  # a person reviewed a movement that needed it
    PERIOD_CLOSED = "period_closed"


class LedgerEntry(Model):
    seq: int
    at: datetime
    kind: LedgerKind
    subject_id: str | None
    payload: dict[str, Any]
    prev_hash: str
    hash: str  # sha256(prev_hash + canonical_json({seq, at, kind, subject_id, payload}))


class LedgerVerification(Model):
    valid: bool
    length: int
    first_broken_seq: int | None
    head_hash: str | None


# ---------------------------------------------------------------------------
# Policy compiler and simulation
# ---------------------------------------------------------------------------


class PolicyChange(Model):
    field: str  # a Policy field name, or "beneficiaries[<id>].agreement" style path
    label: str  # Spanish
    before: Any
    after: Any
    source_quote: str  # the words of the user that justify the change


class SimulatedChange(Model):
    invoice_id: str
    supplier_name: str | None
    before: DecisionStatus
    after: DecisionStatus
    reason: str


class SimulationReport(Model):
    before: Metrics
    after: Metrics
    changed: list[SimulatedChange]


class PolicyProposal(Model):
    text: str
    changes: list[PolicyChange]
    unsupported: list[str]  # parts of the text that map to no rule; shown to the user, never guessed
    questions: list[str] = []  # what the compiler needs clarified before it can apply the text
    proposed: Policy
    simulation: SimulationReport | None = None


# ---------------------------------------------------------------------------
# Adaptive onboarding
# ---------------------------------------------------------------------------


class CompanyProfile(Model):
    """What Custodio infers about a company from its website and first answers, before asking anything else."""

    company_name: str
    website: str | None = None
    industry: str | None = None
    country: str | None = None
    base_currency: str = "USD"
    summary: str | None = None  # Spanish, two sentences, citing the site
    likely_suppliers: list[str] = []  # supplier categories, e.g. "hosting", "nómina tercerizada"
    suggested_rules_text: str | None = None  # a Spanish rules paragraph the user can edit
    evidence_urls: list[str] = []


class SupplierImport(Model):
    beneficiaries: list[Beneficiary]
    warnings: list[str] = []  # rows that could not be read, duplicates, missing accounts


# ---------------------------------------------------------------------------
# Live red team
# ---------------------------------------------------------------------------


class AttackSpec(Model):
    round: int
    technique: str  # short Spanish name, e.g. "Cuenta cambiada con logo idéntico"
    rationale: str  # why the attacker thinks it will pass, informed by earlier verdicts
    target_rules: list[str]
    render_as: Literal["pdf", "text", "image"]
    invoice_text: str  # visible content
    hidden_text: str | None = None  # content to hide (white text, tiny font, metadata)


class RedTeamEvent(Model):
    type: Literal["round_started", "attack_generated", "verdict", "round_finished", "summary", "error"]
    round: int
    attack: AttackSpec | None = None
    decision: Decision | None = None
    caught: bool | None = None  # True when no improper payment happened
    message: str | None = None


# ---------------------------------------------------------------------------
# Payment firewall for other agents (API + MCP) and the public challenge
# ---------------------------------------------------------------------------


class PaymentIntent(Model):
    agent: str  # who is asking, e.g. "claude-desktop" or "erp-bot"
    beneficiary_name: str
    beneficiary_tax_id: str | None = None
    bank_name: str | None = None
    account_number: str
    amount: Amount
    currency: str
    invoice_number: str
    issue_date: date | None = None
    description: str = ""
    document_text: str | None = None  # optional source text; scanned for hidden instructions too


class IntentVerdict(Model):
    decision: Decision
    ledger_hash: str
    acta_url: str


class ChallengeAttempt(Model):
    id: str
    alias: str | None
    technique: str | None
    decision: Decision
    broke_through: bool  # True only if an improper payment happened; the goal is that this is never True
    at: datetime


class ChallengeStats(Model):
    attempts: int
    improper_payments: int
    held: int
    escalated: int
    paid_legitimately: int
    hall_of_fame: list[ChallengeAttempt] = []
