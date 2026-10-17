/**
 * Earned autonomy and the payment calendar for the mock client. It is not the engine: a supplier whose invoice
 * fired a risk signal shows as supervised, everyone else keeps the policy's cap, and nothing is scheduled because
 * the mock pays everything the moment it decides.
 */
import type { ScheduleView, SupplierTrust, TrustOverview } from "../client";
import type { Decision, Policy } from "../contracts";
import type { DemoItem } from "./dataset";

const RISK_SIGNALS = ["R2", "R4", "R5", "R6"];
const CLEAN_PAYMENTS_TO_EARN = 3;
const HORIZON_DAYS = 45;
const DEFAULT_APY = 4;
const DAY_MS = 86_400_000;
export const MOCK_APY_NOTE =
  "Supuesto configurable (CUSTODIO_TREASURY_YIELD_APY), no un dato de Blinka: el rendimiento anual que se asume para el saldo que se queda en la cuenta hasta el día de pago.";

function riskSignal(decision: Decision) {
  return decision.rules.find((rule) => RISK_SIGNALS.includes(rule.rule_id) && ["hold", "escalate"].includes(rule.outcome));
}

function supplierTrust(policy: Policy, beneficiary: Policy["beneficiaries"][number], items: DemoItem[]): SupplierTrust {
  const incident = items
    .filter((item) => item.decision.beneficiary_id === beneficiary.id)
    .map((item) => ({ item, rule: riskSignal(item.decision) }))
    .findLast(({ rule }) => rule !== undefined);
  const floor = policy.trust.floor;
  if (!incident?.rule) {
    return {
      beneficiary_id: beneficiary.id,
      supplier_name: beneficiary.name,
      has_history: false,
      cap: policy.approval_threshold,
      clean_streak: 0,
      supervised: false,
      reason: "Sin historial de confianza: usa el tope de aprobación automática de la política.",
      clean_needed: CLEAN_PAYMENTS_TO_EARN,
      next_cap: null,
      last_incident: null,
      timeline: [],
    };
  }
  const step = {
    seq: 0,
    at: incident.item.received_at,
    kind: "trust_revoked" as const,
    invoice_id: incident.item.decision.invoice_id,
    rule_id: incident.rule.rule_id,
    reason: incident.rule.reason,
    summary: "En supervisión: una persona aprueba cada pago hasta que recupere la confianza.",
    cap_before: policy.approval_threshold,
    cap_after: floor,
    clean_streak: 0,
    hash: "",
  };
  return {
    beneficiary_id: beneficiary.id,
    supplier_name: beneficiary.name,
    has_history: true,
    cap: floor,
    clean_streak: 0,
    supervised: true,
    reason: `En supervisión tras una señal de riesgo: ${incident.rule.reason}`,
    clean_needed: CLEAN_PAYMENTS_TO_EARN,
    next_cap: null,
    last_incident: step,
    timeline: [step],
  };
}

export function mockTrust(policy: Policy, items: DemoItem[], autonomyRate: number): TrustOverview {
  const suppliers = policy.beneficiaries.filter((b) => b.allowed).map((b) => supplierTrust(policy, b, items));
  const days = new Map<string, { decisions: number; alone: number }>();
  for (const { decision, received_at } of items) {
    const day = days.get(received_at.slice(0, 10)) ?? { decisions: 0, alone: 0 };
    day.decisions += 1;
    if (decision.status === "paid_auto" || decision.status === "hold") day.alone += 1;
    days.set(received_at.slice(0, 10), day);
  }
  return {
    base_currency: policy.base_currency,
    autonomy_rate: autonomyRate,
    floor: policy.trust.floor,
    ceiling: policy.trust.hard_ceiling ? policy.approval_threshold : policy.per_payment_limit,
    policy_threshold: policy.approval_threshold,
    hard_ceiling: policy.trust.hard_ceiling,
    clean_payments_to_earn: CLEAN_PAYMENTS_TO_EARN,
    suppliers: suppliers.toSorted((a, b) => Number(b.has_history) - Number(a.has_history)),
    autonomy: [...days.entries()]
      .toSorted(([a], [b]) => a.localeCompare(b))
      .map(([day, { decisions, alone }]) => ({ day, decisions, decided_alone: alone, rate: alone / decisions })),
  };
}

export function mockSchedule(policy: Policy, today: string, balance: number): ScheduleView {
  const start = Date.parse(`${today}T00:00:00Z`);
  return {
    today,
    horizon_days: HORIZON_DAYS,
    base_currency: policy.base_currency,
    rail: "simulated",
    cash: balance,
    committed_balance: balance,
    reserve: policy.reserve,
    apy: DEFAULT_APY,
    apy_note: MOCK_APY_NOTE,
    items: [],
    waiting: [],
    balance: Array.from({ length: HORIZON_DAYS + 1 }, (_, offset) => ({
      day: new Date(start + offset * DAY_MS).toISOString().slice(0, 10),
      balance,
    })),
    captured: {
      year: Number(today.slice(0, 4)),
      month: Number(today.slice(5, 7)),
      discounts: 0,
      late_fees_avoided: 0,
      treasury_yield: 0,
      total: 0,
      payments: 0,
    },
  };
}
