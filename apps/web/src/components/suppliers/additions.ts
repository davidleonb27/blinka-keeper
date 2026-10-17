import type { Beneficiary, Policy } from "@/lib/api/contracts";

export interface SupplierFields {
  name: string;
  tax_id: string;
  bank_name: string;
  account_number: string;
}

export interface SkippedSupplier {
  name: string;
  reason: string;
}

export interface AdditionPlan {
  added: Beneficiary[];
  skipped: SkippedSupplier[];
}

const ALREADY_REGISTERED =
  "Ya está registrado. Sus datos bancarios no se cambian desde aquí: un cambio de cuenta llega en una factura y se verifica fuera de banda (R15).";
const REPEATED = "Está dos veces en la lista; se agrega una sola.";
const INCOMPLETE = "Faltan datos: nombre, identificación tributaria, banco y cuenta.";

function code(text: string): string {
  return text.normalize("NFD").replace(/[^\p{L}\p{N}]/gu, "").toLowerCase();
}

export function supplierFromForm(fields: SupplierFields, currency: string): Beneficiary {
  const trimmed = Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, value.trim()])) as SupplierFields;
  return { ...trimmed, id: `B-${code(trimmed.tax_id).toUpperCase()}`, aliases: [], currency, allowed: true };
}

function isComplete(b: Beneficiary): boolean {
  return [b.name, b.tax_id, b.bank_name, b.account_number].every((value) => value.trim() !== "");
}

function freeId(wanted: string, taken: Set<string>): string {
  let id = wanted;
  for (let n = 2; taken.has(id); n++) id = `${wanted}-${n}`;
  return id;
}

/**
 * Which candidates become new suppliers. Only additions: a candidate that matches a registered supplier by tax id or
 * name is skipped, so this path can never change where an existing supplier gets paid.
 */
export function planAdditions(policy: Policy, candidates: Beneficiary[]): AdditionPlan {
  const known = new Set(policy.beneficiaries.flatMap((b) => [code(b.tax_id), code(b.name)]));
  const ids = new Set(policy.beneficiaries.map((b) => b.id));
  const seen = new Set<string>();
  const plan: AdditionPlan = { added: [], skipped: [] };
  for (const candidate of candidates) {
    const keys = [code(candidate.tax_id), code(candidate.name)];
    const reason = !isComplete(candidate)
      ? INCOMPLETE
      : keys.some((key) => known.has(key))
        ? ALREADY_REGISTERED
        : keys.some((key) => seen.has(key))
          ? REPEATED
          : null;
    if (reason) {
      plan.skipped.push({ name: candidate.name, reason });
      continue;
    }
    keys.forEach((key) => seen.add(key));
    const id = freeId(candidate.id, ids);
    ids.add(id);
    plan.added.push({ ...candidate, id, allowed: true });
  }
  return plan;
}
