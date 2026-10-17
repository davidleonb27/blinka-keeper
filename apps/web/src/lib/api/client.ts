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
  Policy,
  PolicyProposal,
  RedTeamEvent,
  SupplierImport,
} from "./contracts";
import type { components } from "./openapi";

export type Health = components["schemas"]["Health"];

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
  getPolicy(): Promise<Policy>;
  compilePolicy(text: string): Promise<PolicyProposal>;
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
