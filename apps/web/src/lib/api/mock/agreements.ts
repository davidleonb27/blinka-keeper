/**
 * The mock's side of approving with a new agreement: one supplier's agreement changes and nothing else, and the
 * versions come back from the ledger. Suggestions are drawn from the real API's history, so the mock has none.
 */
import type { AgreementInput, PolicyVersion } from "../client";
import type { LedgerEntry, Policy, PolicyChange } from "../contracts";

export interface AgreementChange {
  policy: Policy;
  changes: PolicyChange[];
}

export function withAgreement(policy: Policy, beneficiaryId: string | null, input: AgreementInput, quote: string): AgreementChange {
  const supplier = policy.beneficiaries.find((b) => b.id === beneficiaryId);
  if (!supplier?.agreement) return { policy, changes: [] };
  const before = supplier.agreement;
  const after = {
    ...before,
    amount: input.amount == null ? before.amount : Number(input.amount),
    tolerance_pct: input.tolerance_pct == null ? before.tolerance_pct : Number(input.tolerance_pct),
  };
  const path = `beneficiaries[${supplier.id}].agreement`;
  const changes: PolicyChange[] = [];
  if (after.amount !== before.amount) {
    changes.push({ field: `${path}.amount`, label: `Monto acordado con ${supplier.name}`, before: before.amount, after: after.amount, source_quote: quote });
  }
  const tolerance = (value: number | null | undefined) => value ?? policy.agreement_tolerance_pct;
  if (tolerance(after.tolerance_pct) !== tolerance(before.tolerance_pct)) {
    changes.push({
      field: `${path}.tolerance_pct`,
      label: `Tolerancia de ${supplier.name} (%)`,
      before: tolerance(before.tolerance_pct),
      after: tolerance(after.tolerance_pct),
      source_quote: quote,
    });
  }
  const beneficiaries = policy.beneficiaries.map((b) => (b.id === supplier.id ? { ...b, agreement: after } : b));
  return { policy: { ...policy, beneficiaries }, changes };
}

function text(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

export function versionsOf(ledger: LedgerEntry[]): PolicyVersion[] {
  return ledger
    .filter((entry) => entry.kind === "policy_changed")
    .map((entry) => ({
      version: Number(entry.payload.version ?? 1),
      at: entry.at,
      author: text(entry.payload.author) ?? text(entry.payload.actor),
      reason: text(entry.payload.reason),
      invoice_id: text(entry.payload.invoice_id),
      suggestion_id: null,
      changed_fields: [],
      hash: entry.hash,
    }))
    .reverse();
}
