/**
 * In-memory implementation of CustodioApi over the prototype dataset, for NEXT_PUBLIC_API_MODE=mock.
 * It mimics the API's responses so every screen works without a backend; it is not the engine.
 */
import type {
  ApprovalInput,
  CustodioApi,
  DecisionListItem,
  OnboardingRequest,
  WorkspaceSummary,
} from "../client";
import type { ChallengeStats, Decision, DecisionStatus, LedgerEntry, Metrics, Policy } from "../contracts";
import { InvalidRequestError, NotFoundError } from "../errors";
import { formatMoney } from "../../format";
import { initialChallengeStats, judgeAttempt, recordAttempt } from "./challenge";
import { freshDemo, type DemoDataset, type DemoItem } from "./dataset";
import { appendEntry, verifyChain } from "./ledger";
import { importMockSuppliers, simulateFirstWeek } from "./onboarding";
import { compilePolicyText } from "./policy-compiler";
import { proposeMockProfile } from "./profile";
import { RED_TEAM_SCRIPT, scriptedDecision } from "./red-team-script";

const DEFAULT_LATENCY_MS = 450;
const RED_TEAM_STEP_FACTOR = 2;
const MOCK_API_KEY = "ck_demo_7f3a91c2e4b0";
const CONFLICT = 409;

export interface MockClientOptions {
  latencyMs?: number;
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

export function createMockClient({ latencyMs = DEFAULT_LATENCY_MS }: MockClientOptions = {}): CustodioApi {
  let demo: DemoDataset = freshDemo();
  let stats: ChallengeStats = initialChallengeStats();

  const wait = (factor = 1) =>
    new Promise<void>((resolve) => setTimeout(resolve, latencyMs * factor));

  async function respond<T>(produce: () => T | Promise<T>, factor = 1): Promise<T> {
    await wait(factor);
    return structuredClone(await produce());
  }

  function findItem(invoiceId: string): DemoItem {
    const item = demo.items.find((i) => i.decision.invoice_id === invoiceId);
    if (!item) throw new NotFoundError();
    return item;
  }

  async function record(entry: Omit<LedgerEntry, "seq" | "prev_hash" | "hash">): Promise<LedgerEntry> {
    const appended = await appendEntry(demo.ledger, entry);
    demo.ledger = [...demo.ledger, appended];
    return appended;
  }

  function summary(): WorkspaceSummary {
    const { company, policy, audit } = demo;
    return {
      workspace_id: "ws_demo",
      company_name: company.name,
      today: company.today,
      base_currency: company.base_currency,
      opening_balance: company.opening_balance,
      balance: company.balance_end,
      spent_auto_base: company.spent_auto_base,
      period_budget: policy.period_budget,
      reserve: policy.reserve,
      metrics: metricsOf(demo.items, audit.improper_payments),
      audit,
    };
  }

  function settle(item: DemoItem, input: ApprovalInput, approved: boolean): Decision {
    const decision = item.decision;
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
    const balance = demo.company.balance_end;
    if (balance - amount < demo.policy.reserve) {
      decision.status = "hold";
      decision.blocked_reason = `Pagarlo dejaría el saldo en ${formatMoney(balance - amount, demo.policy.base_currency)}, debajo de la reserva de ${formatMoney(demo.policy.reserve, demo.policy.base_currency)}.`;
      return decision;
    }
    decision.status = "paid_human";
    decision.balance_before = balance;
    decision.balance_after = balance - amount;
    demo.company.balance_end = balance - amount;
    return decision;
  }

  async function decide(invoiceId: string, input: ApprovalInput, approved: boolean): Promise<Decision> {
    const item = findItem(invoiceId);
    if (item.decision.status !== "pending_approval") {
      throw new InvalidRequestError("Esta factura no espera aprobación.", CONFLICT);
    }
    const decision = settle(item, input, approved);
    const entry = await record({
      at: decision.approval?.at ?? nowIso(),
      kind: "approval",
      subject_id: invoiceId,
      payload: { actor: input.approver, decision: decision.approval?.decision, status: decision.status },
    });
    item.ledger = { seq: entry.seq, hash: entry.hash };
    return decision;
  }

  async function applyPolicy(policy: Policy): Promise<Policy> {
    demo.policy = { ...policy, version: demo.policy.version + 1 };
    await record({
      at: nowIso(),
      kind: "policy_changed",
      subject_id: null,
      payload: { actor: "Tú", version: demo.policy.version },
    });
    return demo.policy;
  }

  async function completeOnboarding(request: OnboardingRequest) {
    const firstWeek = simulateFirstWeek(request);
    const items: DemoItem[] = firstWeek.map((item: DecisionListItem) => ({
      ...item,
      extraction: null,
      ledger: null,
      trap: null,
      expected: null,
    }));
    const paid = items.filter((i) => i.decision.status === "paid_auto");
    const spent = paid.reduce((sum, i) => sum + (i.decision.amount_base ?? 0), 0);
    demo = {
      company: {
        ...demo.company,
        name: request.profile.company_name,
        place: request.profile.country ?? "",
        base_currency: request.policy.base_currency,
        opening_balance: request.opening_balance,
        balance_end: request.opening_balance - spent,
        spent_auto_base: spent,
      },
      policy: request.policy,
      metrics: metricsOf(items, 0),
      audit: { agrees: true, checked: paid.length, improper_payments: 0, findings: [] },
      items,
      ledger: [],
    };
    await record({ at: nowIso(), kind: "policy_changed", subject_id: null, payload: { actor: "Onboarding", version: 1 } });
    for (const item of items) {
      const entry = await record({
        at: item.received_at,
        kind: "decision",
        subject_id: item.decision.invoice_id,
        payload: { status: item.decision.status, verdict: item.decision.agent_verdict },
      });
      item.ledger = { seq: entry.seq, hash: entry.hash };
    }
    return { workspace_id: "ws_demo", api_key: MOCK_API_KEY, first_week: firstWeek, metrics: demo.metrics };
  }

  return {
    health: () => respond(() => ({ status: "ok", version: "mock", anthropic: false, gemini: false })),
    createWorkspace: () => respond(() => ({ workspace_id: "ws_demo", api_key: MOCK_API_KEY })),
    getWorkspace: () => respond(summary),
    listDecisions: () =>
      respond(() =>
        demo.items.map(({ decision, received_at, source }) => ({ decision, received_at, source })),
      ),
    getDecision: (id) => respond(() => findItem(id)),
    approveDecision: (id, input) => respond(() => decide(id, input, true)),
    rejectDecision: (id, input) => respond(() => decide(id, input, false)),
    getPolicy: () => respond(() => demo.policy),
    compilePolicy: (text) => respond(() => compilePolicyText(text, demo.policy, demo.items), 2),
    applyPolicy: (policy) => respond(() => applyPolicy(policy)),
    getLedger: () => respond(() => demo.ledger),
    verifyLedger: () => respond(() => verifyChain(demo.ledger)),
    tamperDemo: () =>
      respond(async () => {
        const copy = structuredClone(demo.ledger);
        const target = copy[Math.floor(copy.length / 2)];
        target.payload = { ...target.payload, status: "paid_auto", amount_base: "9800" };
        return { tampered_seq: target.seq, verification: await verifyChain(copy) };
      }),
    getChallengeStats: () => respond(() => stats),
    submitChallengeAttempt: (input) =>
      respond(() => {
        const attempt = judgeAttempt(input, stats.attempts + 1, nowIso());
        stats = recordAttempt(stats, attempt);
        return attempt;
      }, 2),
    proposeProfile: (input) => respond(() => proposeMockProfile(input), 3),
    importSuppliers: async (file) => {
      const text = await file.text();
      return respond(() => importMockSuppliers(file.name, text, demo.policy.base_currency), 2);
    },
    completeOnboarding: (request) => respond(() => completeOnboarding(request), 2),
    runRedTeam: async ({ rounds }, onEvent, signal) => {
      const script = RED_TEAM_SCRIPT.slice(0, rounds);
      for (const [index, round] of script.entries()) {
        if (signal?.aborted) return;
        const number = index + 1;
        onEvent({ type: "round_started", round: number });
        await wait(RED_TEAM_STEP_FACTOR);
        onEvent({ type: "attack_generated", round: number, attack: { ...round.attack, round: number } });
        await wait(RED_TEAM_STEP_FACTOR);
        onEvent({ type: "verdict", round: number, decision: scriptedDecision(round, index), caught: true });
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
