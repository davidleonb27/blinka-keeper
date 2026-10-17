/**
 * The shapes of apps/api/custodio/contracts.py as the API serves them, taken from the generated OpenAPI types
 * (schema.gen.ts) so tsc fails on any drift. Only the rules catalogue and the field list are values here.
 * Models the API both reads and writes come in two flavours: `-Output` is what it answers (amounts are numbers),
 * `-Input` what it accepts; the web reads the first and sends it back, which the second accepts.
 */
import type { components } from "./schema.gen";

type Schemas = components["schemas"];

export type ISODate = string;
export type ISODateTime = string;

// --- Rules catalogue --------------------------------------------------------

export type RuleEffect = "hold" | "escalate";

export interface RuleSpec {
  id: string;
  key: string;
  label: string;
  effect: RuleEffect;
}

/** Mirrors contracts.RULES: fixed ids, evaluated in this order. */
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

export type AgreementKind = Schemas["AgreementKind"];
export type Agreement = Schemas["Agreement-Output"];
export type Beneficiary = Schemas["Beneficiary-Output"];
export type Approver = Schemas["Approver"];
export type Policy = Schemas["Policy-Output"];
export type PolicyInput = Schemas["Policy-Input"];

// --- Reading invoices ------------------------------------------------------

export type Evidence = Schemas["Evidence"];
export type ExtractedField = Schemas["ExtractedField"];
export type HiddenTextKind = Schemas["HiddenTextKind"];
export type HiddenTextFinding = Schemas["HiddenTextFinding"];
export type InvoiceSource = Schemas["InvoiceSource"];
export type ExtractedInvoice = Schemas["ExtractedInvoice"];
export type InvoiceView = Schemas["InvoiceView"];

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
] as const satisfies readonly (keyof ExtractedInvoice)[];

export type ExtractedFieldName = (typeof EXTRACTED_FIELD_NAMES)[number];

// --- Decisions, audit and ledger -------------------------------------------

export type RuleOutcome = Schemas["RuleOutcome"];
export type RuleResult = Schemas["RuleResult"];
export type AgentVerdict = Schemas["AgentVerdict"];
export type DecisionStatus = Schemas["DecisionStatus"];
export type Approval = Schemas["Approval"];
export type PaymentExecution = Schemas["PaymentExecution"];
export type PaymentInstruction = Schemas["PaymentInstruction"];
export type PaymentNetwork = PaymentInstruction["network"];
export type PaymentRailName = PaymentExecution["rail"];
export type ExecutionStatus = PaymentExecution["status"];
export type Decision = Schemas["Decision"];
export type Metrics = Schemas["Metrics"];
export type BatchResult = Schemas["BatchResult"];
export type AuditFinding = Schemas["AuditFinding"];
export type AuditReport = Schemas["AuditReport"];
export type LedgerKind = Schemas["LedgerKind"];
export type LedgerEntry = Schemas["LedgerEntry"];
export type LedgerVerification = Schemas["LedgerVerification"];

// --- Policy compiler and simulation ----------------------------------------

export type PolicyChange = Schemas["PolicyChange"];
export type SimulatedChange = Schemas["SimulatedChange"];
export type SimulationReport = Schemas["SimulationReport"];
export type PolicyProposal = Schemas["PolicyProposal"];

// --- Adaptive onboarding ---------------------------------------------------

export type CompanyProfile = Schemas["CompanyProfile"];
export type SupplierImport = Schemas["SupplierImport"];

// --- Live red team ---------------------------------------------------------

export type AttackSpec = Schemas["AttackSpec"];
export type RedTeamEventType = Schemas["RedTeamEvent"]["type"];
export type RedTeamEvent = Schemas["RedTeamEvent"];

// --- Firewall and public challenge -----------------------------------------

export type ChallengeAttempt = Schemas["ChallengeAttempt"];
export type ChallengeStats = Schemas["ChallengeStats"];
