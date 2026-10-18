/**
 * The one interface every screen talks to. Two implementations: the live client (relative /api/v1) and the mock
 * client (prototype dataset, in memory). Every request and response type comes from the OpenAPI document of the
 * API (schema.gen.ts), keyed by route and method, so a drift on either side fails tsc instead of production.
 */
import type { Beneficiary, CompanyProfile, Decision, LedgerEntry, Policy, PolicyProposal, RedTeamEvent, SupplierImport } from "./contracts";
import type { components, paths } from "./schema.gen";

type Schemas = components["schemas"];

export type ApiPath = keyof paths;
export type Method = "get" | "post" | "put";
type Operation<P extends ApiPath, M extends Method> = NonNullable<paths[P][M]>;
type SuccessContent<R> = R extends { 200: { content: infer C } } ? C : R extends { 201: { content: infer C } } ? C : never;

/** The JSON a route answers on success. */
export type ResponseOf<P extends ApiPath, M extends Method> =
  SuccessContent<Operation<P, M>["responses"]> extends { "application/json": infer T } ? T : never;

/** The JSON body a route accepts. */
export type JsonBodyOf<P extends ApiPath, M extends Method> =
  Operation<P, M> extends { requestBody?: { content: { "application/json": infer B } } } ? B : never;

/** The fields of a multipart route; files travel as `File`. */
export type FormOf<P extends ApiPath, M extends Method> =
  Operation<P, M> extends { requestBody?: { content: { "multipart/form-data": infer F } } } ? F : never;

export type PathParamsOf<P extends ApiPath, M extends Method> =
  Operation<P, M>["parameters"] extends { path: infer T } ? T : never;

export type Health = ResponseOf<"/api/v1/health", "get">;
export type WorkspaceMode = Schemas["WorkspaceMode"];
export type WorkspaceCreated = ResponseOf<"/api/v1/workspaces", "post">;
export type WorkspaceSummary = ResponseOf<"/api/v1/workspaces/current", "get">;
export type DecisionListItem = ResponseOf<"/api/v1/decisions", "get">[number];
export type Acta = ResponseOf<"/api/v1/decisions/{invoice_id}", "get">;
export type ApprovalInput = JsonBodyOf<"/api/v1/decisions/{invoice_id}/approve", "post">;
export type ProcessOutcome = ResponseOf<"/api/v1/invoices/process", "post">;
export type InvoiceForm = FormOf<"/api/v1/invoices", "post">;
export type ReceivedInvoice = ResponseOf<"/api/v1/invoices", "post">;
export type TamperDemoResult = ResponseOf<"/api/v1/ledger/tamper-demo", "post">;
/** `answers` has a server default; the web does not ask for extra answers yet. */
export type ProfileRequest = Pick<JsonBodyOf<"/api/v1/onboarding/profile", "post">, "company_name" | "website">;
export type OnboardingRequest = JsonBodyOf<"/api/v1/onboarding/complete", "post">;
export type OnboardingResult = ResponseOf<"/api/v1/onboarding/complete", "post">;
export type RedTeamRequest = JsonBodyOf<"/api/v1/redteam/runs", "post">;
export type ChallengeForm = FormOf<"/api/v1/challenge/attempts", "post">;
export type TrustOverview = ResponseOf<"/api/v1/trust", "get">;
export type SupplierTrust = TrustOverview["suppliers"][number];
export type TrustStep = SupplierTrust["timeline"][number];
export type SimulationResult = ResponseOf<"/api/v1/trust/simulate", "post">;
export type ScheduleView = ResponseOf<"/api/v1/schedule", "get">;
export type ScheduledItem = ScheduleView["items"][number];
export type RunDueResult = ResponseOf<"/api/v1/schedule/run-due", "post">;
export type ReconciliationForm = FormOf<"/api/v1/reconciliations", "post">;
export type ReconciliationView = ResponseOf<"/api/v1/reconciliations/{reconciliation_id}", "get">;
export type ReconciliationItem = ResponseOf<"/api/v1/reconciliations", "get">[number];
export type ResolveInput = JsonBodyOf<"/api/v1/reconciliations/{reconciliation_id}/resolve", "post">;
export type PeriodCloseView = ResponseOf<"/api/v1/periods/{period}/close", "post">;
export type DemoStatementFormat = "csv" | "pdf";
export type WhatsAppStatus = ResponseOf<"/api/v1/whatsapp/link", "get">;
export type WhatsAppLinkCode = ResponseOf<"/api/v1/whatsapp/link-codes", "post">;

/** An invoice of the company's own: a PDF or image, or the text of an email. */
export interface InvoiceInput {
  file?: File | null;
  text?: string | null;
}

export interface ChallengeInput {
  text: string;
  alias: string | null;
  /** A PDF or image instead of text. */
  file?: File | null;
}

/** A bank statement to reconcile: a CSV, PDF or image the person dropped, or the demo statement. */
export interface StatementInput {
  file?: File | null;
  demo?: boolean;
}

/** The ledger entry that sealed the decision of an acta: the last one about that invoice. */
export function sealOf(acta: Pick<Acta, "ledger">): LedgerEntry | null {
  return acta.ledger.at(-1) ?? null;
}

export interface CustodioApi {
  health(): Promise<Health>;
  createWorkspace(mode: WorkspaceMode): Promise<WorkspaceCreated>;
  getWorkspace(): Promise<WorkspaceSummary>;
  /** Receives one invoice; it waits undecided until `processInvoices`. */
  uploadInvoice(input: InvoiceInput): Promise<ReceivedInvoice>;
  processInvoices(): Promise<ProcessOutcome>;
  listDecisions(): Promise<DecisionListItem[]>;
  getDecision(invoiceId: string): Promise<Acta>;
  approveDecision(invoiceId: string, input: ApprovalInput): Promise<Decision>;
  rejectDecision(invoiceId: string, input: ApprovalInput): Promise<Decision>;
  /** Retries a payment whose execution failed; a payment that already went out comes back unchanged. */
  executePayment(invoiceId: string): Promise<Decision>;
  getPolicy(): Promise<Policy>;
  /** Compiles against `base` when given (onboarding draft), otherwise the workspace policy. */
  compilePolicy(text: string, base?: Policy): Promise<PolicyProposal>;
  applyPolicy(policy: Policy): Promise<Policy>;
  /** Appends new suppliers; the server refuses one that matches a registered supplier. */
  addSuppliers(beneficiaries: Beneficiary[]): Promise<Policy>;
  getLedger(): Promise<LedgerEntry[]>;
  verifyLedger(): Promise<ResponseOf<"/api/v1/ledger/verify", "get">>;
  tamperDemo(): Promise<TamperDemoResult>;
  runRedTeam(
    request: RedTeamRequest,
    onEvent: (event: RedTeamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void>;
  getChallengeStats(): Promise<ResponseOf<"/api/v1/challenge/stats", "get">>;
  submitChallengeAttempt(input: ChallengeInput): Promise<ResponseOf<"/api/v1/challenge/attempts", "post">>;
  proposeProfile(request: ProfileRequest): Promise<CompanyProfile>;
  /** `currency` is for rows that do not say theirs; without it, the workspace's base currency. */
  importSuppliers(file: File, currency?: string): Promise<SupplierImport>;
  completeOnboarding(request: OnboardingRequest): Promise<OnboardingResult>;
  /** Each supplier's earned auto-approval cap, folded from its trust entries in the ledger. */
  getTrust(): Promise<TrustOverview>;
  /** Plays the demo's seeded month once, on the simulated rail; calling it again changes nothing. */
  simulateMonth(): Promise<SimulationResult>;
  getSchedule(): Promise<ScheduleView>;
  /** Pays what is due today or earlier through the configured rail. */
  runDuePayments(): Promise<RunDueResult>;
  listReconciliations(): Promise<ReconciliationItem[]>;
  getReconciliation(id: string): Promise<ReconciliationView>;
  reconcileStatement(input: StatementInput): Promise<ReconciliationView>;
  /** A person marks a movement that needed review as reviewed; the note stays in the ledger. */
  resolveMovement(id: string, input: ResolveInput): Promise<ReconciliationView>;
  closePeriod(period: string, closedBy: string): Promise<PeriodCloseView>;
  downloadEvidence(period: string): Promise<Blob>;
  downloadDemoStatement(format: DemoStatementFormat): Promise<Blob>;
  /** Whether invoices can arrive on WhatsApp here, the phones linked (masked) and when the last one arrived. */
  getWhatsAppStatus(): Promise<WhatsAppStatus>;
  /** A one-time code that links the phone that sends it to this workspace. */
  createWhatsAppCode(): Promise<WhatsAppLinkCode>;
}
