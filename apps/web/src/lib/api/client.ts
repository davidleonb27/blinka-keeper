/**
 * The one interface every screen talks to. Two implementations: the live client (relative /api/v1) and the mock
 * client (prototype dataset, in memory). Every request and response type comes from the OpenAPI document of the
 * API (schema.gen.ts), keyed by route and method, so a drift on either side fails tsc instead of production.
 */
import type { CompanyProfile, Decision, LedgerEntry, Policy, PolicyProposal, RedTeamEvent, SupplierImport } from "./contracts";
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
export type TamperDemoResult = ResponseOf<"/api/v1/ledger/tamper-demo", "post">;
/** `answers` has a server default; the web does not ask for extra answers yet. */
export type ProfileRequest = Pick<JsonBodyOf<"/api/v1/onboarding/profile", "post">, "company_name" | "website">;
export type OnboardingRequest = JsonBodyOf<"/api/v1/onboarding/complete", "post">;
export type OnboardingResult = ResponseOf<"/api/v1/onboarding/complete", "post">;
export type RedTeamRequest = JsonBodyOf<"/api/v1/redteam/runs", "post">;
export type ChallengeForm = FormOf<"/api/v1/challenge/attempts", "post">;

export interface ChallengeInput {
  text: string;
  alias: string | null;
  /** A PDF or image instead of text. */
  file?: File | null;
}

/** The ledger entry that sealed the decision of an acta: the last one about that invoice. */
export function sealOf(acta: Pick<Acta, "ledger">): LedgerEntry | null {
  return acta.ledger.at(-1) ?? null;
}

export interface CustodioApi {
  health(): Promise<Health>;
  createWorkspace(mode: WorkspaceMode): Promise<WorkspaceCreated>;
  getWorkspace(): Promise<WorkspaceSummary>;
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
  importSuppliers(file: File): Promise<SupplierImport>;
  completeOnboarding(request: OnboardingRequest): Promise<OnboardingResult>;
}
