// Ports the prototype's demo company (prototype/engine.js) into contract-shaped JSON for mock mode.
// Run with `npm run gen:mock`. The output is data, not logic: the web never decides.
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const E = require("../../../prototype/engine.js");
const OUTPUT = fileURLToPath(new URL("../src/lib/api/mock/demo-dataset.json", import.meta.url));

const BOGOTA_UTC_OFFSET_HOURS = 5;
const FIRST_DECISION_HOUR = 9;
const MINUTES_BETWEEN_INVOICES = 7;
const GENESIS_HASH = "0".repeat(64);
const SOURCE = { email: "email", pdf: "pdf", whatsapp: "whatsapp", imagen: "image" };
const STATUS = { pay: "paid_auto", hold: "hold", escalate: "pending_approval" };
const OUTCOME = { ok: "pass", skip: "skipped" };

const rules = E.defaultRules();
const results = E.decideAll(E.dataset().map((doc) => E.extract(doc, rules)), rules, {});
const audit = E.audit(results, rules);

function bogotaToUtc(day, minutes) {
  const date = new Date(`${day}T00:00:00Z`);
  date.setUTCHours(FIRST_DECISION_HOUR + BOGOTA_UTC_OFFSET_HOURS, minutes);
  return date.toISOString().replace(".000Z", "Z");
}

function receivedTimes() {
  const times = new Map();
  let day = "";
  let minutes = 0;
  for (const result of results) {
    if (result.inv.receivedAt !== day) [day, minutes] = [result.inv.receivedAt, 0];
    minutes += MINUTES_BETWEEN_INVOICES;
    times.set(result.id, bogotaToUtc(day, minutes));
  }
  return times;
}

function accountNumber(last4) {
  return `•••• ${last4}`;
}

function beneficiary(b) {
  return {
    id: b.id,
    name: b.name,
    tax_id: b.taxId,
    aliases: [],
    country: b.country,
    bank_name: b.bank,
    account_number: accountNumber(b.last4),
    currency: b.agreement.currency,
    agreement: {
      kind: b.agreement.kind === "cap" ? "monthly_cap" : "fixed",
      amount: b.agreement.amount,
      currency: b.agreement.currency,
      tolerance_pct: null,
      source: `Acuerdo: ${b.agreement.label}`,
      early_payment_discount: null,
      late_fee_pct: null,
      critical: false,
    },
    allowed: b.allowed,
    approver_contact: null,
  };
}

const policy = {
  version: 1,
  base_currency: "USD",
  approval_threshold: rules.approvalThresholdUSD,
  per_payment_limit: rules.perPaymentLimitUSD,
  period_budget: rules.periodBudgetUSD,
  reserve: rules.reserveUSD,
  agreement_tolerance_pct: rules.agreementTolerancePct,
  duplicate_window_days: rules.duplicateWindowDays,
  split_window_days: rules.splitWindowDays,
  min_confidence: rules.minConfidence,
  allowed_currencies: rules.allowedCurrencies,
  beneficiaries: rules.beneficiaries.map(beneficiary),
  approvers: [
    { name: "Ana Gómez", role: "CFO", email: "ana@cobalto.example" },
    { name: "Tomás Rivera", role: "Controller", email: "tomas@cobalto.example" },
  ],
  trust: { floor: 0, hard_ceiling: false },
};

function field(inv, value, spanKey, confidenceKey) {
  const span = inv.spans[spanKey];
  const confidence = value == null ? 0 : (inv.confidence[confidenceKey] ?? 0.98);
  const evidence = span
    ? { quote: inv.raw.slice(span[0], span[1]), page: 1, char_start: span[0], char_end: span[1] }
    : null;
  return { value, evidence, confidence, verified: evidence !== null && confidence >= rules.minConfidence };
}

function extraction(inv) {
  return {
    document_id: `doc-${inv.id}`,
    source: SOURCE[inv.channel],
    supplier_name: field(inv, inv.vendorName, "vendor", "vendor"),
    supplier_tax_id: field(inv, inv.taxId, "taxId", "taxId"),
    invoice_number: field(inv, inv.number, "number", "number"),
    issue_date: field(inv, null, "issue", "issue"),
    due_date: field(inv, inv.due, "due", "due"),
    amount: field(inv, Number.isFinite(inv.amount) ? inv.amount.toFixed(2) : null, "amount", "amount"),
    currency: field(inv, inv.currency, "amount", "currency"),
    bank_name: field(inv, inv.bank, "account", "account"),
    account_number: field(inv, inv.last4, "account", "account"),
    description: field(inv, inv.concept, "concept", "number"),
    visible_text: inv.raw,
    hidden_findings: inv.hiddenText
      ? [
          {
            kind: "invisible_color",
            text: inv.hiddenText,
            page: 1,
            detail: "Texto blanco sobre fondo blanco en la página 1, escrito para un agente de IA.",
          },
        ]
      : [],
    reader: "datos de ejemplo del prototipo",
    overall_confidence: Math.min(...Object.values(inv.confidence).filter((c) => c > 0)),
  };
}

function ruleResult(check) {
  return {
    rule_id: check.id,
    key: check.key,
    label: check.label,
    outcome: OUTCOME[check.status] ?? check.effect,
    reason: check.detail,
    facts: {},
  };
}

function decision(result) {
  return {
    invoice_id: result.id,
    beneficiary_id: result.ben?.id ?? null,
    supplier_name: result.ben?.name ?? result.inv.vendorName,
    amount: Number.isFinite(result.inv.amount) ? result.inv.amount : null,
    currency: result.inv.currency,
    amount_base: Number.isFinite(result.usd) ? Math.round(result.usd * 100) / 100 : null,
    agent_verdict: result.agent,
    status: STATUS[result.status],
    rules: result.checks.map(ruleResult),
    explanation: result.explanation,
    counterfactual: result.agent === "pay" ? null : result.counterfactual.join(" "),
    narrative: null,
    balance_before: Math.round(result.balanceBefore * 100) / 100,
    balance_after: Math.round(result.balanceAfter * 100) / 100,
    approval: null,
    blocked_reason: null,
  };
}

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function chain(events) {
  const entries = [];
  let prevHash = GENESIS_HASH;
  events.forEach((event, index) => {
    const body = { seq: index + 1, at: event.at, kind: event.kind, subject_id: event.subject_id, payload: event.payload };
    const hash = createHash("sha256").update(prevHash + canonicalJson(body)).digest("hex");
    entries.push({ ...body, prev_hash: prevHash, hash });
    prevHash = hash;
  });
  return entries;
}

const times = receivedTimes();
const decisions = results.map(decision);
const ledger = chain([
  {
    at: "2026-10-01T13:00:00Z",
    kind: "policy_changed",
    subject_id: null,
    payload: {
      actor: "Ana Gómez (CFO)",
      summary: `Reglas iniciales: tope USD ${policy.approval_threshold}, límite USD ${policy.per_payment_limit}, cupo USD ${policy.period_budget}, reserva USD ${policy.reserve}.`,
      version: 1,
    },
  },
  ...decisions.map((d) => ({
    at: times.get(d.invoice_id),
    kind: "decision",
    subject_id: d.invoice_id,
    payload: { actor: "Custodio (agente)", status: d.status, verdict: d.agent_verdict, amount_base: String(d.amount_base) },
  })),
]);
const seqOf = new Map(ledger.filter((e) => e.subject_id).map((e) => [e.subject_id, e]));

const items = results.map((result, index) => ({
  decision: decisions[index],
  received_at: times.get(result.id),
  source: SOURCE[result.inv.channel],
  extraction: extraction(result.inv),
  ledger: { seq: seqOf.get(result.id).seq, hash: seqOf.get(result.id).hash },
  trap: result.inv.trap,
  expected: result.inv.expected,
}));

const count = (status) => decisions.filter((d) => d.status === status).length;
const correct = results.filter((r) => r.agent === r.inv.expected).length;

const dataset = {
  company: {
    name: E.COMPANY.name,
    place: E.COMPANY.place,
    today: E.TODAY,
    base_currency: "USD",
    opening_balance: rules.openingBalanceUSD,
    balance_end: Math.round(results.balanceEnd * 100) / 100,
    spent_auto_base: Math.round(results.spentEnd * 100) / 100,
    fx_units_per_base: E.UNITS_PER_USD,
  },
  policy,
  metrics: {
    total: decisions.length,
    paid_auto: count("paid_auto"),
    paid_human: 0,
    hold: count("hold"),
    pending: count("pending_approval"),
    rejected: 0,
    autonomy_rate: (count("paid_auto") + count("hold")) / decisions.length,
    accuracy: correct / decisions.length,
    improper_payments: audit.violations.length,
  },
  audit: { agrees: audit.violations.length === 0, checked: audit.checked, improper_payments: audit.violations.length, findings: [] },
  items,
  ledger,
};

writeFileSync(OUTPUT, `${JSON.stringify(dataset, null, 2)}\n`);
console.log(`wrote ${items.length} decisions and ${ledger.length} ledger entries to ${OUTPUT}`);
