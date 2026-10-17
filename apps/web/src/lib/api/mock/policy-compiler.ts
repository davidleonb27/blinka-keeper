/**
 * Mock stand-in for the API's rules compiler (Claude Opus in production). It recognises a handful of
 * phrasings so mock mode feels alive; anything else is returned as unsupported, never guessed.
 */
import type {
  DecisionStatus,
  Metrics,
  Policy,
  PolicyChange,
  PolicyProposal,
  SimulatedChange,
} from "../contracts";
import { formatMoney } from "../../format";
import { normalize } from "../../text";
import type { DemoItem } from "./dataset";

type NumericField =
  | "approval_threshold"
  | "per_payment_limit"
  | "period_budget"
  | "reserve"
  | "agreement_tolerance_pct";

const FIELD_LABELS: Record<NumericField, string> = {
  approval_threshold: "Tope de aprobación automática",
  per_payment_limit: "Límite por pago",
  period_budget: "Cupo de pago automático",
  reserve: "Reserva que no se toca",
  agreement_tolerance_pct: "Tolerancia frente a lo acordado",
};

// Order matters: the more specific phrasing wins.
const FIELD_PATTERNS: [NumericField, RegExp][] = [
  ["per_payment_limit", /limite (?:por|de cada|para cada) pago/],
  ["period_budget", /presupuesto|cupo/],
  ["reserve", /reserva/],
  ["agreement_tolerance_pct", /tolerancia/],
  ["approval_threshold", /aprob|permiso|persona|pregunt|sobre|mas de|encima de|supere/],
];

const AMOUNT = /(\d[\d.,]*)\s*(k\b|mil\b|millon(?:es)?\b)?/;
const BLOCK = /(?:bloquea|no (?:le )?pagues? (?:mas )?a)\s+(?:a\s+)?(.+)/;
const APPROVER = /(?:apruebe|autorice)\s+([a-zñ]+)/;
const CLAUSE_SPLIT = /\.(?=\s|$)|[;\n]+|\s+y\s+(?=(?:la|el|bloquea|pide|nada|el cupo|la reserva)\b)/i;
const MULTIPLIERS: Record<string, number> = { k: 1e3, mil: 1e3, millon: 1e6, millones: 1e6 };

export function parseAmountPhrase(normalized: string): number | null {
  const match = AMOUNT.exec(normalized);
  if (!match) return null;
  const digits = match[1].replace(/[.,](?=\d{3}\b)/g, "").replace(",", ".");
  const value = Number.parseFloat(digits) * (match[2] ? MULTIPLIERS[match[2]] : 1);
  return Number.isFinite(value) ? value : null;
}

function splitClauses(text: string): string[] {
  return text
    .split(CLAUSE_SPLIT)
    .map((clause) => clause.trim())
    .filter(Boolean);
}

interface ClauseResult {
  change?: PolicyChange;
  question?: string;
}

function blockClause(clause: string, normalized: string, policy: Policy): ClauseResult | null {
  const match = BLOCK.exec(normalized);
  if (!match) return null;
  const target = match[1].trim();
  const beneficiary = policy.beneficiaries.find((b) => normalize(b.name).includes(target));
  if (!beneficiary) {
    return { question: `No encontré a «${target}» entre tus proveedores. ¿Cuál es su NIT y su cuenta?` };
  }
  return {
    change: {
      field: `beneficiaries[${beneficiary.id}].allowed`,
      label: `${beneficiary.name}: beneficiario permitido`,
      before: beneficiary.allowed ?? true,
      after: false,
      source_quote: clause,
    },
  };
}

function numericClause(clause: string, normalized: string, policy: Policy): ClauseResult | null {
  const amount = parseAmountPhrase(normalized);
  const entry = FIELD_PATTERNS.find(([, pattern]) => pattern.test(normalized));
  if (amount === null || !entry) return null;
  const [field] = entry;
  const approver = APPROVER.exec(normalized)?.[1];
  const knownApprover =
    !approver || policy.approvers.some((a) => normalize(a.name).startsWith(approver));
  return {
    change: { field, label: FIELD_LABELS[field], before: policy[field], after: amount, source_quote: clause },
    question: knownApprover
      ? undefined
      : `¿Quién es «${approver}»? Agrégala como aprobadora con su Telegram para que le lleguen las actas.`,
  };
}

function applyChange(policy: Policy, change: PolicyChange): Policy {
  const blocked = /^beneficiaries\[(.+)\]\.allowed$/.exec(change.field);
  if (blocked) {
    return {
      ...policy,
      beneficiaries: policy.beneficiaries.map((b) => (b.id === blocked[1] ? { ...b, allowed: false } : b)),
    };
  }
  return { ...policy, [change.field]: change.after, version: policy.version + 1 };
}

function failingRuleKeys(item: DemoItem): string[] {
  return item.decision.rules.filter((r) => r.outcome === "hold" || r.outcome === "escalate").map((r) => r.key);
}

function simulatedStatus(item: DemoItem, policy: Policy): { status: DecisionStatus; reason: string } {
  const { status, amount_base: amount, beneficiary_id } = item.decision;
  const base = policy.base_currency;
  if (status === "paid_auto" && amount !== null) {
    if (amount > policy.approval_threshold) {
      return { status: "pending_approval", reason: `Supera el tope de ${formatMoney(policy.approval_threshold, base)}.` };
    }
    if (amount > policy.per_payment_limit) {
      return { status: "pending_approval", reason: `Supera el límite por pago de ${formatMoney(policy.per_payment_limit, base)}.` };
    }
    if (policy.beneficiaries.some((b) => b.id === beneficiary_id && b.allowed === false)) {
      return { status: "pending_approval", reason: "El proveedor quedó bloqueado." };
    }
  }
  const onlyOverThreshold = failingRuleKeys(item).every((key) => key === "approval");
  if (status === "pending_approval" && onlyOverThreshold && amount !== null && amount <= policy.approval_threshold) {
    return { status: "paid_auto", reason: `Queda dentro del nuevo tope de ${formatMoney(policy.approval_threshold, base)}.` };
  }
  return { status, reason: "" };
}

function metricsFor(statuses: DecisionStatus[], improper: number): Metrics {
  const count = (s: DecisionStatus) => statuses.filter((x) => x === s).length;
  const total = statuses.length;
  return {
    total,
    paid_auto: count("paid_auto"),
    paid_human: count("paid_human"),
    hold: count("hold"),
    pending: count("pending_approval"),
    rejected: count("rejected"),
    autonomy_rate: total ? (count("paid_auto") + count("hold")) / total : 0,
    accuracy: null,
    improper_payments: improper,
  };
}

export function compilePolicyText(text: string, policy: Policy, items: DemoItem[]): PolicyProposal {
  const changes: PolicyChange[] = [];
  const unsupported: string[] = [];
  const questions: string[] = [];
  for (const clause of splitClauses(text)) {
    const normalized = normalize(clause);
    const result = blockClause(clause, normalized, policy) ?? numericClause(clause, normalized, policy);
    if (!result) unsupported.push(clause);
    const change = result?.change;
    const isNew = change && change.before !== change.after && !changes.some((c) => c.field === change.field);
    if (change && isNew) changes.push(change);
    if (result?.question) questions.push(result.question);
  }
  const proposed = changes.reduce(applyChange, policy);
  const simulated = items.map((item) => ({ item, ...simulatedStatus(item, proposed) }));
  const changed: SimulatedChange[] = simulated
    .filter(({ item, status }) => item.decision.status !== status)
    .map(({ item, status, reason }) => ({
      invoice_id: item.decision.invoice_id,
      supplier_name: item.decision.supplier_name,
      before: item.decision.status,
      after: status,
      reason,
    }));
  return {
    text,
    changes,
    unsupported,
    questions,
    proposed,
    simulation: changes.length
      ? {
          before: metricsFor(items.map((i) => i.decision.status), 0),
          after: metricsFor(simulated.map((s) => s.status), 0),
          changed,
        }
      : null,
  };
}
