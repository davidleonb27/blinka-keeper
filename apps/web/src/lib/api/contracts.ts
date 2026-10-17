/**
 * Mirror of apps/api/custodio/contracts.py. Money is a JSON number; dates are ISO-8601 strings.
 * Keep field names identical to the Python models: this file is the seam with the API.
 */

export type ISODate = string;
export type ISODateTime = string;

export type RuleEffect = "hold" | "escalate";

export interface RuleSpec {
  id: string;
  key: string;
  label: string;
  effect: RuleEffect;
}

export const RULES: readonly RuleSpec[] = [
  { id: "R1", key: "reading", label: "Lectura confiable", effect: "escalate" },
  { id: "R2", key: "injection", label: "Sin instrucciones escondidas", effect: "escalate" },
  { id: "R3", key: "beneficiary", label: "Beneficiario permitido", effect: "escalate" },
  { id: "R4", key: "account", label: "Cuenta registrada", effect: "hold" },
  { id: "R5", key: "duplicate", label: "Sin cobro duplicado", effect: "hold" },
  { id: "R6", key: "agreement", label: "Coincide con lo acordado", effect: "escalate" },
  { id: "R7", key: "split", label: "Sin pagos fraccionados", effect: "escalate" },
  { id: "R8", key: "currency", label: "Moneda permitida", effect: "hold" },
  { id: "R9", key: "approval", label: "Tope de aprobación automática", effect: "escalate" },
  { id: "R10", key: "limit", label: "Límite por pago", effect: "escalate" },
  { id: "R11", key: "budget", label: "Cupo de pago automático", effect: "escalate" },
  { id: "R12", key: "reserve", label: "Saldo y reserva", effect: "hold" },
];

// --- Company configuration -------------------------------------------------

export type AgreementKind = "fixed" | "monthly_cap";

export interface Agreement {
  kind: AgreementKind;
  amount: number;
  currency: string;
  tolerance_pct?: number | null;
  source?: string | null;
}

export interface Beneficiary {
  id: string;
  name: string;
  tax_id: string;
  aliases?: string[];
  country?: string | null;
  bank_name: string;
  account_number: string;
  currency: string;
  agreement?: Agreement | null;
  allowed?: boolean;
  approver_contact?: string | null;
}

export interface Approver {
  name: string;
  role?: string | null;
  telegram_chat_id?: string | null;
  email?: string | null;
}

export interface Policy {
  version: number;
  base_currency: string;
  approval_threshold: number;
  per_payment_limit: number;
  period_budget: number;
  reserve: number;
  agreement_tolerance_pct: number;
  duplicate_window_days: number;
  split_window_days: number;
  min_confidence: number;
  allowed_currencies: string[];
  beneficiaries: Beneficiary[];
  approvers: Approver[];
}

// --- Reading invoices ------------------------------------------------------

export interface Evidence {
  quote: string;
  page?: number | null;
  char_start?: number | null;
  char_end?: number | null;
}

export interface ExtractedField {
  value: string | null;
  evidence?: Evidence | null;
  confidence: number;
  verified: boolean;
}

export type HiddenTextKind =
  | "invisible_color"
  | "tiny_font"
  | "off_page"
  | "covered"
  | "metadata"
  | "instruction";

export interface HiddenTextFinding {
  kind: HiddenTextKind;
  text: string;
  page?: number | null;
  detail: string;
}

export type InvoiceSource = "pdf" | "image" | "text" | "email" | "whatsapp" | "intent";

export const EXTRACTED_FIELD_NAMES = [
  "supplier_name",
  "supplier_tax_id",
  "invoice_number",
  "issue_date",
  "due_date",
  "amount",
  "currency",
  "bank_name",
  "account_number",
  "description",
] as const;

export type ExtractedFieldName = (typeof EXTRACTED_FIELD_NAMES)[number];

export type ExtractedInvoice = Record<ExtractedFieldName, ExtractedField> & {
  document_id: string;
  source: InvoiceSource;
  visible_text: string;
  hidden_findings: HiddenTextFinding[];
  reader: string;
  overall_confidence: number;
};

// --- Decisions, audit and ledger -------------------------------------------

export type RuleOutcome = "pass" | "hold" | "escalate" | "skipped";

export interface RuleResult {
  rule_id: string;
  key: string;
  label: string;
  outcome: RuleOutcome;
  reason: string;
  facts?: Record<string, unknown>;
}

export type AgentVerdict = "pay" | "hold" | "escalate";

export type DecisionStatus = "paid_auto" | "paid_human" | "hold" | "pending_approval" | "rejected";

export interface Approval {
  invoice_id: string;
  decision: "approved" | "rejected";
  approver: string;
  channel: "web" | "telegram" | "api";
  at: ISODateTime;
  note?: string | null;
}

export interface Decision {
  invoice_id: string;
  beneficiary_id: string | null;
  supplier_name: string | null;
  amount: number | null;
  currency: string | null;
  amount_base: number | null;
  agent_verdict: AgentVerdict;
  status: DecisionStatus;
  rules: RuleResult[];
  explanation: string;
  counterfactual: string | null;
  narrative?: string | null;
  balance_before?: number | null;
  balance_after?: number | null;
  approval?: Approval | null;
  blocked_reason?: string | null;
}

export interface Metrics {
  total: number;
  paid_auto: number;
  paid_human: number;
  hold: number;
  pending: number;
  rejected: number;
  autonomy_rate: number;
  accuracy?: number | null;
  improper_payments: number;
}

export interface AuditFinding {
  invoice_id: string;
  severity: "critical" | "warning";
  message: string;
}

export interface AuditReport {
  agrees: boolean;
  checked: number;
  improper_payments: number;
  findings: AuditFinding[];
}

export type LedgerKind =
  | "policy_changed"
  | "invoice_received"
  | "decision"
  | "approval"
  | "payment"
  | "redteam_attack"
  | "challenge_attempt"
  | "intent";

export interface LedgerEntry {
  seq: number;
  at: ISODateTime;
  kind: LedgerKind;
  subject_id: string | null;
  payload: Record<string, unknown>;
  prev_hash: string;
  hash: string;
}

export interface LedgerVerification {
  valid: boolean;
  length: number;
  first_broken_seq: number | null;
  head_hash: string | null;
}

// --- Policy compiler and simulation ----------------------------------------

export interface PolicyChange {
  field: string;
  label: string;
  before: unknown;
  after: unknown;
  source_quote: string;
}

export interface SimulatedChange {
  invoice_id: string;
  supplier_name: string | null;
  before: DecisionStatus;
  after: DecisionStatus;
  reason: string;
}

export interface SimulationReport {
  before: Metrics;
  after: Metrics;
  changed: SimulatedChange[];
}

export interface PolicyProposal {
  text: string;
  changes: PolicyChange[];
  unsupported: string[];
  questions: string[];
  proposed: Policy;
  simulation?: SimulationReport | null;
}

// --- Adaptive onboarding ---------------------------------------------------

export interface CompanyProfile {
  company_name: string;
  website?: string | null;
  industry?: string | null;
  country?: string | null;
  base_currency: string;
  summary?: string | null;
  likely_suppliers: string[];
  suggested_rules_text?: string | null;
  evidence_urls: string[];
}

export interface SupplierImport {
  beneficiaries: Beneficiary[];
  warnings: string[];
}

// --- Live red team ---------------------------------------------------------

export interface AttackSpec {
  round: number;
  technique: string;
  rationale: string;
  target_rules: string[];
  render_as: "pdf" | "text" | "image";
  invoice_text: string;
  hidden_text?: string | null;
}

export type RedTeamEventType =
  | "round_started"
  | "attack_generated"
  | "verdict"
  | "round_finished"
  | "summary"
  | "error";

export interface RedTeamEvent {
  type: RedTeamEventType;
  round: number;
  attack?: AttackSpec | null;
  decision?: Decision | null;
  caught?: boolean | null;
  message?: string | null;
}

// --- Firewall and public challenge -----------------------------------------

export interface ChallengeAttempt {
  id: string;
  alias: string | null;
  technique: string | null;
  decision: Decision;
  broke_through: boolean;
  at: ISODateTime;
}

export interface ChallengeStats {
  attempts: number;
  improper_payments: number;
  held: number;
  escalated: number;
  paid_legitimately: number;
  hall_of_fame: ChallengeAttempt[];
}
