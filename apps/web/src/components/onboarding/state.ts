/** Onboarding answers and the pure rules that validate them and turn them into an API request. */
import type { OnboardingRequest, OnboardingResult } from "@/lib/api/client";
import type { Approver, Beneficiary, CompanyProfile, Policy, PolicyProposal } from "@/lib/api/contracts";

export const STEPS = ["company", "profile", "money", "approvers", "rules", "suppliers", "simulation", "ready"] as const;
export type StepId = (typeof STEPS)[number];

export const CURRENCIES = ["USD", "COP", "MXN", "BRL", "CLP"] as const;

interface StarterMoney {
  balance: number;
  reserve: number;
  threshold: number;
  limit: number;
  budget: number;
}

// Sensible first numbers per currency; the person edits them and the rules step overrides them.
const STARTER_MONEY: Record<string, StarterMoney> = {
  USD: { balance: 50_000, reserve: 15_000, threshold: 2_000, limit: 8_000, budget: 20_000 },
  COP: { balance: 200_000_000, reserve: 60_000_000, threshold: 8_000_000, limit: 30_000_000, budget: 80_000_000 },
  MXN: { balance: 900_000, reserve: 270_000, threshold: 36_000, limit: 140_000, budget: 360_000 },
  BRL: { balance: 270_000, reserve: 80_000, threshold: 10_000, limit: 40_000, budget: 100_000 },
  CLP: { balance: 47_000_000, reserve: 14_000_000, threshold: 1_900_000, limit: 7_500_000, budget: 19_000_000 },
};

// The defaults of contracts.Policy for the rules a new company rarely tunes on day one.
const POLICY_DEFAULTS = {
  agreement_tolerance_pct: 2,
  duplicate_window_days: 20,
  split_window_days: 2,
  min_confidence: 0.9,
} satisfies Partial<Policy>;

export function starterMoney(currency: string): StarterMoney {
  return STARTER_MONEY[currency] ?? STARTER_MONEY.USD;
}

export interface ApproverDraft {
  name: string;
  role: string;
  telegram: string;
}

export interface Answers {
  companyName: string;
  website: string;
  profile: CompanyProfile | null;
  country: string;
  currency: string;
  balance: string;
  reserve: string;
  approvers: ApproverDraft[];
  rulesText: string;
  proposal: PolicyProposal | null;
  suppliers: Beneficiary[];
  supplierWarnings: string[];
  result: OnboardingResult | null;
}

export const EMPTY_APPROVER: ApproverDraft = { name: "", role: "", telegram: "" };

export const INITIAL_ANSWERS: Answers = {
  companyName: "",
  website: "",
  profile: null,
  country: "CO",
  currency: "COP",
  balance: "",
  reserve: "",
  approvers: [EMPTY_APPROVER],
  rulesText: "",
  proposal: null,
  suppliers: [],
  supplierWarnings: [],
  result: null,
};

/** "200.000.000", "200000000" or "200 000 000" → 200000000. Decimals are not asked for here. */
export function parseWholeAmount(text: string): number | null {
  const digits = text.replace(/[^\d]/g, "");
  return digits ? Number(digits) : null;
}

export function normalizeWebsite(text: string): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

/** Applies a proposed profile, keeping anything the person already typed. */
export function withProfile(answers: Answers, profile: CompanyProfile): Answers {
  const currency = profile.base_currency;
  const money = starterMoney(currency);
  return {
    ...answers,
    profile,
    country: profile.country ?? answers.country,
    currency,
    balance: answers.balance || String(money.balance),
    reserve: answers.reserve || String(money.reserve),
    rulesText: answers.rulesText || (profile.suggested_rules_text ?? ""),
  };
}

export function fallbackProfile(answers: Answers): CompanyProfile {
  return {
    company_name: answers.companyName.trim(),
    website: normalizeWebsite(answers.website),
    industry: null,
    country: answers.country,
    base_currency: answers.currency,
    summary: null,
    likely_suppliers: [],
    suggested_rules_text: null,
    evidence_urls: [],
  };
}

type Validator = (answers: Answers) => string | null;

const VALIDATORS: Partial<Record<StepId, Validator>> = {
  company: (a) => (a.companyName.trim() ? null : "Escribe el nombre de tu empresa para seguir."),
  money: (a) => {
    const balance = parseWholeAmount(a.balance);
    const reserve = parseWholeAmount(a.reserve) ?? 0;
    if (!balance) return "Escribe el saldo disponible.";
    return reserve < balance ? null : "La reserva tiene que ser menor que el saldo.";
  },
  approvers: (a) => (a.approvers.some((p) => p.name.trim()) ? null : "Agrega al menos una persona que apruebe."),
  rules: (a) => (a.rulesText.trim() ? null : "Escribe al menos una regla o usa la sugerida."),
  suppliers: (a) => (a.suppliers.length ? null : "Sube una lista o usa la de ejemplo."),
  simulation: (a) => (a.result ? null : "Custodio todavía está decidiendo tu primera semana."),
};

export function validateStep(step: StepId, answers: Answers): string | null {
  return VALIDATORS[step]?.(answers) ?? null;
}

export function approversOf(answers: Answers): Approver[] {
  return answers.approvers
    .filter((p) => p.name.trim())
    .map((p) => ({
      name: p.name.trim(),
      role: p.role.trim() || null,
      telegram_chat_id: p.telegram.trim() || null,
      email: null,
    }));
}

/** The policy before the person's own words are compiled into it. */
export function draftPolicy(answers: Answers): Policy {
  const money = starterMoney(answers.currency);
  return {
    version: 1,
    base_currency: answers.currency,
    approval_threshold: money.threshold,
    per_payment_limit: money.limit,
    period_budget: money.budget,
    reserve: parseWholeAmount(answers.reserve) ?? money.reserve,
    ...POLICY_DEFAULTS,
    allowed_currencies: [answers.currency],
    beneficiaries: [],
    approvers: approversOf(answers),
  };
}

export function onboardingRequest(answers: Answers): OnboardingRequest {
  const rules = answers.proposal?.proposed ?? draftPolicy(answers);
  return {
    profile: answers.profile ?? fallbackProfile(answers),
    opening_balance: parseWholeAmount(answers.balance) ?? 0,
    policy: { ...rules, approvers: approversOf(answers), beneficiaries: answers.suppliers },
  };
}
