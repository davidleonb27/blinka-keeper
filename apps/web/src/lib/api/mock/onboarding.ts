/**
 * Mock stand-ins for supplier import and the first-week simulation. In production both run in the API
 * (Claude reads the file; the engine decides). Here they only produce believable contract-shaped data.
 */
import type { BatchResult, Beneficiary, Decision, Metrics, Policy, SupplierImport } from "../contracts";
import { formatMoney } from "../../format";
import { decisionFrom, type FailingRules } from "./decision-builder";

const MIN_COLUMNS = 4;

const SAMPLE_SUPPLIERS: [string, string, string, string, number][] = [
  ["Distribuidora Andina SAS", "900.112.334-5", "Bancolombia", "•••• 1204", 3200000],
  ["Nube Segura SAS", "901.554.210-3", "Davivienda", "•••• 7781", 890000],
  ["Transportes El Cóndor", "800.443.981-2", "Banco de Bogotá", "•••• 3390", 1450000],
  ["Contadora Laura Méndez", "1.020.774.551", "Nequi", "•••• 6612", 2100000],
  ["Empaques Verdes SAS", "901.882.004-7", "BBVA Colombia", "•••• 0458", 5600000],
];

function supplier(
  index: number,
  [name, taxId, bank, account, amount]: [string, string, string, string, number],
  currency: string,
): Beneficiary {
  return {
    id: `s${index + 1}`,
    name,
    tax_id: taxId,
    aliases: [],
    country: null,
    bank_name: bank,
    account_number: account,
    currency,
    agreement: { kind: "fixed", amount, currency, tolerance_pct: null, source: "Importado" },
    allowed: true,
    approver_contact: null,
  };
}

function parseRows(text: string): { rows: string[][]; skipped: number } {
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const cells = lines.map((line) => line.split(/[;,\t]/).map((c) => c.trim()));
  const body = cells.filter((row, index) => !(index === 0 && /nombre|name/i.test(row[0] ?? "")));
  const rows = body.filter((row) => row.length >= MIN_COLUMNS && row.every(Boolean));
  return { rows, skipped: body.length - rows.length };
}

export function importMockSuppliers(fileName: string, text: string, currency: string): SupplierImport {
  const { rows, skipped } = /\.(csv|txt|tsv)$/i.test(fileName) ? parseRows(text) : { rows: [], skipped: 0 };
  if (rows.length === 0) {
    return {
      beneficiaries: SAMPLE_SUPPLIERS.map((row, i) => supplier(i, row, currency)),
      warnings: [
        `No pudimos leer filas de «${fileName}» en modo demostración; cargamos una lista de ejemplo para que sigas.`,
      ],
    };
  }
  const beneficiaries = rows.map(([name, taxId, bank, account, amount], i) =>
    supplier(i, [name, taxId, bank, account, Number(amount?.replace(/[^\d]/g, "")) || 0], currency),
  );
  return {
    beneficiaries,
    warnings: skipped ? [`${skipped} filas sin cuenta o sin identificación fiscal quedaron por fuera.`] : [],
  };
}

interface WeekState {
  balance: number;
  spent: number;
  decisions: Decision[];
}

function moneyFailures(amount: number, state: WeekState, policy: Policy): FailingRules {
  const base = policy.base_currency;
  const failing: FailingRules = {};
  if (amount > policy.approval_threshold) {
    failing.approval = `${formatMoney(amount, base)} supera el tope de aprobación automática de ${formatMoney(policy.approval_threshold, base)}.`;
  }
  if (state.spent + amount > policy.period_budget) {
    failing.budget = `Con este pago el agente llegaría a ${formatMoney(state.spent + amount, base)}; su cupo es ${formatMoney(policy.period_budget, base)}.`;
  }
  if (state.balance - amount < policy.reserve) {
    failing.reserve = `Pagar dejaría el saldo en ${formatMoney(state.balance - amount, base)}, debajo de la reserva de ${formatMoney(policy.reserve, base)}.`;
  }
  return failing;
}

function addInvoice(state: WeekState, policy: Policy, b: Beneficiary, amount: number): WeekState {
  const failing = moneyFailures(amount, state, policy);
  const number = `SIM-${String(state.decisions.length + 1).padStart(3, "0")}`;
  const decision = decisionFrom({
    invoice_id: number,
    beneficiary_id: b.id,
    supplier_name: b.name,
    amount,
    currency: policy.base_currency,
    amount_base: amount,
    failing,
    counterfactual: "Para pagarse sola necesita cumplir las reglas que fallaron o la aprobación de una persona.",
    balance_before: state.balance,
    balance_after: Object.keys(failing).length ? state.balance : state.balance - amount,
  });
  const paid = decision.status === "paid_auto";
  return {
    balance: paid ? state.balance - amount : state.balance,
    spent: paid ? state.spent + amount : state.spent,
    decisions: [...state.decisions, decision],
  };
}

function metricsOf(decisions: Decision[]): Metrics {
  const count = (status: Decision["status"]) => decisions.filter((d) => d.status === status).length;
  const total = decisions.length;
  return {
    total,
    paid_auto: count("paid_auto"),
    paid_human: count("paid_human"),
    hold: count("hold"),
    pending: count("pending_approval"),
    rejected: count("rejected"),
    autonomy_rate: total ? (count("paid_auto") + count("hold")) / total : 0,
    accuracy: null,
    improper_payments: 0,
  };
}

/** Like the API: one invoice per supplier with an agreement, exactly as agreed; decided, never stored. */
export function simulateFirstWeek(policy: Policy, openingBalance: number): BatchResult {
  const contracted = policy.beneficiaries.filter((b) => b.agreement);
  let state: WeekState = { balance: openingBalance, spent: 0, decisions: [] };
  for (const b of contracted) state = addInvoice(state, policy, b, b.agreement?.amount ?? 0);
  return {
    decisions: state.decisions,
    spent_auto_base: state.spent,
    balance_end: state.balance,
    metrics: metricsOf(state.decisions),
  };
}
