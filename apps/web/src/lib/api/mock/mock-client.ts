/**
 * In-memory implementation of CustodioApi over the prototype dataset, for NEXT_PUBLIC_API_MODE=mock.
 * It answers exactly the shapes the API answers (the types come from its OpenAPI document) and follows the same
 * flow: a demo workspace starts with its invoices received but undecided until they are processed. It is not the
 * engine: the decisions were computed by the prototype ahead of time.
 */
import type {
  ApprovalInput,
  CustodioApi,
  OnboardingRequest,
  OnboardingResult,
  ProcessOutcome,
  TamperDemoResult,
  WorkspaceMode,
  WorkspaceSummary,
} from "../client";
import type {
  AuditReport,
  Beneficiary,
  ChallengeStats,
  Decision,
  DecisionStatus,
  LedgerEntry,
  Metrics,
  Policy,
  PolicyInput,
} from "../contracts";
import { InvalidRequestError, NotFoundError } from "../errors";
import { formatMoney } from "../../format";
import { initialChallengeStats, judgeAttempt, recordAttempt } from "./challenge";
import { actaOf, DEMO, freshDemo, simulatedExecution, type DemoDataset, type DemoItem } from "./dataset";
import { mockSchedule, mockTrust } from "./autonomy";
import { appendEntry, verifyChain } from "./ledger";
import { importMockSuppliers, simulateFirstWeek } from "./onboarding";
import { compilePolicyText } from "./policy-compiler";
import { proposeMockProfile } from "./profile";
import { createMockReconciliations } from "./reconciliation";
import { RED_TEAM_SCRIPT, scriptedDecision } from "./red-team-script";

const DEFAULT_LATENCY_MS = 450;
const RED_TEAM_STEP_FACTOR = 2;
const MOCK_WORKSPACE_ID = "ws_demo";
export const MOCK_API_KEY = "cus_demo_7f3a91c2e4b0";
const BLANK_COMPANY_NAME = "Mi empresa";
const TAMPER_MARK = "alterado";
const CONFLICT = 409;
const NOTHING_AUDITED: AuditReport = { agrees: true, checked: 0, improper_payments: 0, findings: [] };

export interface MockClientOptions {
  latencyMs?: number;
}

interface MockWorkspace {
  data: DemoDataset;
  /** False while the demo invoices are received but not decided, as in a fresh API demo workspace. */
  processed: boolean;
}

function metricsOf(items: DemoItem[], improper: number): Metrics {
  const statuses = items.map((item) => item.decision.status);
  const count = (status: DecisionStatus) => statuses.filter((s) => s === status).length;
  const total = statuses.length;
  const labelled = items.filter((item) => item.expected !== null);
  const correct = labelled.filter((item) => item.decision.agent_verdict === item.expected).length;
  return {
    total,
    paid_auto: count("paid_auto"),
    paid_human: count("paid_human"),
    hold: count("hold"),
    pending: count("pending_approval"),
    rejected: count("rejected"),
    autonomy_rate: total ? (count("paid_auto") + count("hold")) / total : 0,
    accuracy: labelled.length ? correct / labelled.length : null,
    improper_payments: improper,
  };
}

function nowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function beneficiaryFrom(input: OnboardingRequest["suppliers"][number]): Beneficiary {
  const { agreement } = input;
  return {
    ...input,
    agreement: agreement && {
      ...agreement,
      amount: Number(agreement.amount),
      tolerance_pct: agreement.tolerance_pct == null ? null : Number(agreement.tolerance_pct),
      early_payment_discount: agreement.early_payment_discount && {
        ...agreement.early_payment_discount,
        percent: Number(agreement.early_payment_discount.percent),
      },
      late_fee_pct: agreement.late_fee_pct == null ? null : Number(agreement.late_fee_pct),
    },
  };
}

/** What the API stores for a policy it accepts: amounts as numbers. */
function policyFrom(input: PolicyInput): Policy {
  return {
    ...input,
    approval_threshold: Number(input.approval_threshold),
    per_payment_limit: Number(input.per_payment_limit),
    period_budget: Number(input.period_budget),
    reserve: Number(input.reserve),
    agreement_tolerance_pct: Number(input.agreement_tolerance_pct),
    min_confidence: Number(input.min_confidence),
    beneficiaries: input.beneficiaries.map(beneficiaryFrom),
    trust: { floor: Number(input.trust?.floor ?? 0), hard_ceiling: input.trust?.hard_ceiling ?? false },
  };
}

function demoWorkspace(): MockWorkspace {
  const data = freshDemo();
  // The prototype's decision entries are appended again when the invoices are processed.
  return { data: { ...data, ledger: data.ledger.filter((entry) => entry.kind === "policy_changed") }, processed: false };
}

function blankWorkspace(): MockWorkspace {
  const { company, policy } = DEMO;
  return {
    data: {
      company: { ...company, name: BLANK_COMPANY_NAME, opening_balance: 0, balance_end: 0, spent_auto_base: 0 },
      policy: { ...policy, beneficiaries: [], approvers: [] },
      metrics: metricsOf([], 0),
      audit: NOTHING_AUDITED,
      items: [],
      ledger: [],
    },
    processed: true,
  };
}

export function createMockClient({ latencyMs = DEFAULT_LATENCY_MS }: MockClientOptions = {}): CustodioApi {
  let workspace: MockWorkspace = demoWorkspace();
  let stats: ChallengeStats = initialChallengeStats();
  const reconciliations = createMockReconciliations();

  const wait = (factor = 1) =>
    new Promise<void>((resolve) => setTimeout(resolve, latencyMs * factor));

  async function respond<T>(produce: () => T | Promise<T>, factor = 1): Promise<T> {
    await wait(factor);
    return structuredClone(await produce());
  }

  const decided = (): DemoItem[] => (workspace.processed ? workspace.data.items : []);

  function findItem(invoiceId: string): DemoItem {
    const item = decided().find((i) => i.decision.invoice_id === invoiceId);
    if (!item) throw new NotFoundError();
    return item;
  }

  async function record(entry: Omit<LedgerEntry, "seq" | "prev_hash" | "hash">): Promise<LedgerEntry> {
    const appended = await appendEntry(workspace.data.ledger, entry);
    workspace.data.ledger = [...workspace.data.ledger, appended];
    return appended;
  }

  function summary(): WorkspaceSummary {
    const { company, policy, audit, items } = workspace.data;
    const { processed } = workspace;
    return {
      workspace_id: MOCK_WORKSPACE_ID,
      company_name: company.name,
      today: company.today,
      base_currency: policy.base_currency,
      opening_balance: company.opening_balance,
      balance: processed ? company.balance_end : company.opening_balance,
      spent_auto_base: processed ? company.spent_auto_base : 0,
      reserve: policy.reserve,
      period_budget: policy.period_budget,
      policy_version: policy.version,
      pending_invoices: processed ? 0 : items.length,
      metrics: metricsOf(decided(), processed ? audit.improper_payments : 0),
      audit: processed ? audit : NOTHING_AUDITED,
    };
  }

  async function processInvoices(): Promise<ProcessOutcome> {
    const fresh = workspace.processed ? [] : workspace.data.items;
    workspace.processed = true;
    for (const { decision, received_at } of fresh) {
      await record({
        at: received_at,
        kind: "decision",
        subject_id: decision.invoice_id,
        payload: { actor: "Custodio (agente)", status: decision.status, agent_verdict: decision.agent_verdict },
      });
    }
    const { company, audit } = workspace.data;
    return {
      batch: {
        decisions: fresh.map((item) => item.decision),
        spent_auto_base: company.spent_auto_base,
        balance_end: company.balance_end,
        metrics: metricsOf(fresh, 0),
      },
      audit: fresh.length ? audit : NOTHING_AUDITED,
      vetoed: [],
    };
  }

  function settle(item: DemoItem, input: ApprovalInput, approved: boolean): Decision {
    const { decision } = item;
    const { company, policy } = workspace.data;
    const at = nowIso();
    decision.approval = {
      invoice_id: decision.invoice_id,
      decision: approved ? "approved" : "rejected",
      approver: input.approver,
      channel: "web",
      at,
      note: input.note ?? null,
    };
    if (!approved) {
      decision.status = "rejected";
      return decision;
    }
    const amount = decision.amount_base ?? 0;
    const balance = company.balance_end;
    if (balance - amount < policy.reserve) {
      decision.status = "hold";
      decision.blocked_reason = `Pagarlo dejaría el saldo en ${formatMoney(balance - amount, policy.base_currency)}, debajo de la reserva de ${formatMoney(policy.reserve, policy.base_currency)}.`;
      return decision;
    }
    decision.status = "paid_human";
    decision.balance_before = balance;
    decision.balance_after = balance - amount;
    decision.execution = simulatedExecution(at);
    company.balance_end = balance - amount;
    return decision;
  }

  function executePayment(invoiceId: string): Decision {
    const decision = findItem(invoiceId).decision;
    if (!decision.execution) {
      throw new InvalidRequestError("Esta decisión no tiene un pago fallido que reintentar.", CONFLICT);
    }
    if (decision.execution.status === "failed") decision.execution = simulatedExecution(nowIso());
    return decision;
  }

  async function decide(invoiceId: string, input: ApprovalInput, approved: boolean): Promise<Decision> {
    const item = findItem(invoiceId);
    if (item.decision.status !== "pending_approval") {
      throw new InvalidRequestError("Esta factura no espera aprobación.", CONFLICT);
    }
    const decision = settle(item, input, approved);
    await record({
      at: decision.approval?.at ?? nowIso(),
      kind: "approval",
      subject_id: invoiceId,
      payload: { actor: input.approver, decision: decision.approval?.decision, status: decision.status },
    });
    return decision;
  }

  async function applyPolicy(policy: Policy): Promise<Policy> {
    workspace.data.policy = { ...policy, version: workspace.data.policy.version + 1 };
    await record({
      at: nowIso(),
      kind: "policy_changed",
      subject_id: `policy-v${workspace.data.policy.version}`,
      payload: { actor: "Tú", version: workspace.data.policy.version },
    });
    return workspace.data.policy;
  }

  async function tamperDemo(): Promise<TamperDemoResult> {
    const { ledger } = workspace.data;
    const copy = structuredClone(ledger);
    const target = copy.at(-1);
    if (!target) throw new NotFoundError();
    target.payload = { ...target.payload, [TAMPER_MARK]: true };
    return {
      altered_seq: target.seq,
      altered_field: "payload",
      tampered: await verifyChain(copy),
      real: await verifyChain(ledger),
    };
  }

  async function completeOnboarding(request: OnboardingRequest): Promise<OnboardingResult> {
    const base = request.profile.base_currency;
    const requested = policyFrom(request.policy);
    const suppliers = request.suppliers.map(beneficiaryFrom);
    const policy: Policy = {
      ...requested,
      base_currency: base,
      beneficiaries: suppliers.length ? suppliers : requested.beneficiaries,
      version: workspace.data.policy.version + 1,
    };
    const opening = Number(request.opening_balance);
    workspace = {
      data: {
        ...workspace.data,
        company: {
          ...workspace.data.company,
          name: request.profile.company_name,
          base_currency: base,
          opening_balance: opening,
          balance_end: opening,
          spent_auto_base: 0,
        },
        policy,
        audit: NOTHING_AUDITED,
        items: [],
      },
      processed: true,
    };
    await record({
      at: nowIso(),
      kind: "policy_changed",
      subject_id: `policy-v${policy.version}`,
      payload: { actor: "Onboarding", version: policy.version },
    });
    return { workspace: summary(), first_week: simulateFirstWeek(policy, opening) };
  }

  function createWorkspace(mode: WorkspaceMode) {
    workspace = mode === "blank" ? blankWorkspace() : demoWorkspace();
    return { workspace_id: MOCK_WORKSPACE_ID, api_key: MOCK_API_KEY };
  }

  return {
    health: () => respond(() => ({ status: "ok", version: "mock", anthropic: false, payment_rail: "simulated" as const })),
    createWorkspace: (mode) => respond(() => createWorkspace(mode)),
    getWorkspace: () => respond(summary),
    processInvoices: () => respond(processInvoices, 2),
    listDecisions: () =>
      respond(() => decided().map(({ decision, received_at, source }) => ({ decision, received_at, source }))),
    getDecision: (id) => respond(() => actaOf(findItem(id), workspace.data.ledger)),
    approveDecision: (id, input) => respond(() => decide(id, input, true)),
    rejectDecision: (id, input) => respond(() => decide(id, input, false)),
    executePayment: (id) => respond(() => executePayment(id)),
    getPolicy: () => respond(() => workspace.data.policy),
    compilePolicy: (text, base) =>
      respond(
        () =>
          base
            ? { ...compilePolicyText(text, base, []), simulation: null }
            : compilePolicyText(text, workspace.data.policy, decided()),
        2,
      ),
    applyPolicy: (policy) => respond(() => applyPolicy(policy)),
    getLedger: () => respond(() => workspace.data.ledger),
    verifyLedger: () => respond(() => verifyChain(workspace.data.ledger)),
    tamperDemo: () => respond(tamperDemo),
    getChallengeStats: () => respond(() => stats),
    submitChallengeAttempt: async (input) => {
      const text = input.file ? await input.file.text() : input.text;
      return respond(() => {
        const attempt = judgeAttempt({ ...input, text }, stats.attempts + 1, nowIso());
        stats = recordAttempt(stats, attempt);
        return attempt;
      }, 2);
    },
    proposeProfile: (input) => respond(() => proposeMockProfile(input), 3),
    importSuppliers: async (file) => {
      const text = await file.text();
      return respond(() => importMockSuppliers(file.name, text, workspace.data.policy.base_currency), 2);
    },
    completeOnboarding: (request) => respond(() => completeOnboarding(request), 2),
    getTrust: () => respond(() => mockTrust(workspace.data.policy, decided(), summary().metrics.autonomy_rate)),
    simulateMonth: () =>
      respond(() => {
        throw new InvalidRequestError("La simulación de 30 días corre en la API real, no en el modo de prueba.", CONFLICT);
      }),
    getSchedule: () => respond(() => mockSchedule(workspace.data.policy, summary().today, summary().balance)),
    runDuePayments: () =>
      respond(() => ({ executed: [], schedule: mockSchedule(workspace.data.policy, summary().today, summary().balance) })),
    listReconciliations: () => respond(() => reconciliations.list()),
    getReconciliation: (id) => respond(() => reconciliations.get(id)),
    reconcileStatement: () =>
      respond(async () => {
        const view = reconciliations.reconcile(nowIso());
        await record({ at: nowIso(), kind: "reconciliation", subject_id: view.id, payload: { summary: "Extracto de demo" } });
        return view;
      }, 2),
    resolveMovement: (id, input) =>
      respond(() =>
        reconciliations.resolve(id, input, () =>
          record({
            at: nowIso(),
            kind: "reconciliation_review",
            subject_id: id,
            payload: { actor: input.reviewer, summary: input.note },
          }),
        ),
      ),
    closePeriod: (period, closedBy) =>
      respond(() =>
        reconciliations.close(period, closedBy, () =>
          record({
            at: nowIso(),
            kind: "period_closed",
            subject_id: `periodo-${period}`,
            payload: { actor: closedBy, summary: `Cierre de ${period}` },
          }),
        ),
      ),
    downloadEvidence: () => respond(() => reconciliations.files()),
    downloadDemoStatement: () => respond(() => reconciliations.files()),
    runRedTeam: async ({ rounds }, onEvent, signal) => {
      const script = RED_TEAM_SCRIPT.slice(0, rounds);
      for (const [index, round] of script.entries()) {
        if (signal?.aborted) return;
        const number = index + 1;
        const attack = { ...round.attack, round: number };
        onEvent({ type: "round_started", round: number });
        await wait(RED_TEAM_STEP_FACTOR);
        onEvent({ type: "attack_generated", round: number, attack });
        await wait(RED_TEAM_STEP_FACTOR);
        onEvent({ type: "verdict", round: number, attack, decision: scriptedDecision(round, index), caught: true });
        onEvent({ type: "round_finished", round: number });
        await wait();
      }
      onEvent({
        type: "summary",
        round: script.length,
        message: `${script.length} ataques, ${script.length} atrapados, 0 pagos indebidos. Las reglas no cambiaron.`,
      });
    },
  };
}
