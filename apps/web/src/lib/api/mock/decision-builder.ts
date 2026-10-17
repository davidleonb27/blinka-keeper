/** Builds contract-shaped decisions for mock responses from the reasons each failing rule gives. */
import type { AgentVerdict, Decision, DecisionStatus, RuleResult } from "../contracts";
import { RULES } from "../contracts";

const STATUS_OF: Record<AgentVerdict, DecisionStatus> = {
  hold: "hold",
  escalate: "pending_approval",
  pay: "paid_auto",
};

export type FailingRules = Partial<Record<string, string>>;

export function ruleResults(failing: FailingRules, passing: FailingRules = {}): RuleResult[] {
  return RULES.map((rule) => {
    const reason = failing[rule.key];
    return {
      rule_id: rule.id,
      key: rule.key,
      label: rule.label,
      outcome: reason ? rule.effect : "pass",
      reason: reason ?? passing[rule.key] ?? "Cumple.",
      facts: {},
    };
  });
}

export interface DecisionDraft {
  invoice_id: string;
  supplier_name: string | null;
  amount: number | null;
  currency: string | null;
  amount_base?: number | null;
  beneficiary_id?: string | null;
  failing: FailingRules;
  passing?: FailingRules;
  counterfactual: string;
  balance_before?: number;
  balance_after?: number;
}

export function decisionFrom(draft: DecisionDraft): Decision {
  const rules = ruleResults(draft.failing, draft.passing);
  const reasons = Object.values(draft.failing).join(" ");
  const holds = rules.some((r) => r.outcome === "hold");
  const escalates = rules.some((r) => r.outcome === "escalate");
  const verdict: AgentVerdict = holds ? "hold" : escalates ? "escalate" : "pay";
  const explanation = {
    hold: `Se retiene: no se paga. ${reasons}`,
    escalate: `Se pide permiso a una persona. ${reasons} El agente no paga esto sin aprobación.`,
    pay: "Se paga sola: cumple las doce reglas.",
  }[verdict];
  return {
    invoice_id: draft.invoice_id,
    beneficiary_id: draft.beneficiary_id ?? null,
    supplier_name: draft.supplier_name,
    amount: draft.amount,
    currency: draft.currency,
    amount_base: draft.amount_base ?? null,
    agent_verdict: verdict,
    status: STATUS_OF[verdict],
    rules,
    explanation,
    counterfactual: verdict === "pay" ? null : draft.counterfactual,
    balance_before: draft.balance_before ?? null,
    balance_after: draft.balance_after ?? null,
  };
}
