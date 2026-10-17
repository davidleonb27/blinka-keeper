/**
 * The one interface every screen talks to. Two implementations: the live client (relative /api/v1)
 * and the mock client (prototype dataset, in memory). Envelope types that contracts.py does not
 * define yet are proposed to lane L4 in docs/lanes/reports/L5.md.
 */
import type {
  AuditReport,
  ChallengeAttempt,
  ChallengeStats,
  CompanyProfile,
  Decision,
  ExtractedInvoice,
  InvoiceSource,
  ISODate,
  ISODateTime,
  LedgerEntry,
  LedgerVerification,
  Metrics,
  PaymentRailName,
  Policy,
  PolicyProposal,
  RedTeamEvent,
  SupplierImport,
} from "./contracts";
import type { components } from "./openapi";

/** Only the fields the web reads, so it holds whether or not the API still reports retired providers. */
export type Health = Pick<components["schemas"]["Health"], "status" | "version" | "anthropic"> & {
  payment_rail: PaymentRailName;
};

export type WorkspaceMode = "demo" | "blank";

export interface WorkspaceCreated {
  workspace_id: string;
  api_key: string;
}

export interface WorkspaceSummary {
  workspace_id: string;
  company_name: string;
  today: ISODate;
  base_currency: string;
  opening_balance: number;
  balance: number;
  spent_auto_base: number;
  period_budget: number;
  reserve: number;
  metrics: Metrics;
  audit: AuditReport;
}

export interface DecisionListItem {
  decision: Decision;
  received_at: ISODateTime;
  source: InvoiceSource;
}

export interface LedgerPointer {
  seq: number;
  hash: string;
}

export interface DecisionDetail extends DecisionListItem {
  extraction: ExtractedInvoice | null;
  ledger: LedgerPointer | null;
  trap: string | null;
}

export interface ApprovalInput {
  approver: string;
  note?: string;
}

export interface TamperDemoResult {
  tampered_seq: number;
  verification: LedgerVerification;
}

export interface ProfileRequest {
  company_name: string;
  website: string | null;
}

export interface OnboardingRequest {
  profile: CompanyProfile;
  opening_balance: number;
  policy: Policy;
}

export interface OnboardingResult {
  workspace_id: string;
  api_key: string;
  first_week: DecisionListItem[];
  metrics: Metrics;
}

export interface ChallengeInput {
  text: string;
  alias: string | null;
  /** A PDF or image instead of text; sent as multipart. */
  file?: File | null;
}

export interface RedTeamRequest {
  rounds: number;
}

export interface CustodioApi {
  health(): Promise<Health>;
  createWorkspace(mode: WorkspaceMode): Promise<WorkspaceCreated>;
  getWorkspace(): Promise<WorkspaceSummary>;
  listDecisions(): Promise<DecisionListItem[]>;
  getDecision(invoiceId: string): Promise<DecisionDetail>;
  approveDecision(invoiceId: string, input: ApprovalInput): Promise<Decision>;
  rejectDecision(invoiceId: string, input: ApprovalInput): Promise<Decision>;
  /** Retries a payment whose execution failed; a payment that already went out comes back unchanged. */
  executePayment(invoiceId: string): Promise<Decision>;
  getPolicy(): Promise<Policy>;
  /** Compiles against `base` when given (onboarding draft), otherwise the workspace policy. */
  compilePolicy(text: string, base?: Policy): Promise<PolicyProposal>;
  applyPolicy(policy: Policy): Promise<Policy>;
  getLedger(): Promise<LedgerEntry[]>;
  verifyLedger(): Promise<LedgerVerification>;
  tamperDemo(): Promise<TamperDemoResult>;
  runRedTeam(
    request: RedTeamRequest,
    onEvent: (event: RedTeamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void>;
  getChallengeStats(): Promise<ChallengeStats>;
  submitChallengeAttempt(input: ChallengeInput): Promise<ChallengeAttempt>;
  proposeProfile(request: ProfileRequest): Promise<CompanyProfile>;
  importSuppliers(file: File): Promise<SupplierImport>;
  completeOnboarding(request: OnboardingRequest): Promise<OnboardingResult>;
}
