/**
 * Mock stand-ins for supplier import and the first-week simulation. In production both run in the API
 * (Claude reads the file; the engine decides). Here they only produce believable contract-shaped data.
 */
import type { DecisionListItem, OnboardingRequest } from "../client";
import type { Beneficiary, Policy, SupplierImport } from "../contracts";
import { formatMoney } from "../../format";
import { decisionFrom, type FailingRules } from "./decision-builder";

const MIN_COLUMNS = 4;
const FIRST_WEEK_SUPPLIERS = 5;
const MONDAY = "2026-10-19";

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
  items: DecisionListItem[];
}

function receivedAt(index: number): string {
  const day = Number(MONDAY.slice(-2)) + Math.floor(index / 2);
  return `${MONDAY.slice(0, -2)}${day}T${index % 2 ? "19" : "14"}:10:00Z`;
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

function addInvoice(state: WeekState, policy: Policy, b: Beneficiary, amount: number, trap: FailingRules): WeekState {
  const failing = { ...moneyFailures(amount, state, policy), ...trap };
  const decision = decisionFrom({
    invoice_id: `S-${String(state.items.length + 1).padStart(3, "0")}`,
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
    items: [...state.items, { decision, received_at: receivedAt(state.items.length), source: "pdf" }],
  };
}

export function simulateFirstWeek({ policy, opening_balance }: OnboardingRequest): DecisionListItem[] {
  const suppliers = policy.beneficiaries.slice(0, FIRST_WEEK_SUPPLIERS);
  const amountOf = (b: Beneficiary) => b.agreement?.amount ?? policy.approval_threshold / 2;
  let state: WeekState = { balance: opening_balance, spent: 0, items: [] };
  for (const b of suppliers) state = addInvoice(state, policy, b, amountOf(b), {});
  const [first, second, third] = suppliers;
  if (first) {
    state = addInvoice(state, policy, first, amountOf(first), {
      account: `La factura pide pagar a otra cuenta; la registrada de ${first.name} es ${first.bank_name} ${first.account_number}.`,
    });
  }
  if (second) {
    state = addInvoice(state, policy, second, amountOf(second), {
      duplicate: `Ya llegó un cobro de ${second.name} por el mismo monto esta semana.`,
    });
  }
  if (third) {
    state = addInvoice(state, policy, third, amountOf(third), {
      injection: "El PDF trae texto invisible dirigido al agente. El agente no obedece texto de las facturas.",
    });
  }
  return state.items;
}
