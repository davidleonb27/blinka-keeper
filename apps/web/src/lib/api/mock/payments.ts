/** /pagos in the mock: the demo pays on the simulated rail, so there is no Stripe to match or to ask. */
import type { PaymentsOverview, StripeProof } from "../client";
import type { Decision, Policy } from "../contracts";

const PAID: ReadonlySet<Decision["status"]> = new Set(["paid_auto", "paid_human"]);
const NOT_STRIPE = "Este pago no salió por Stripe, así que no hay transferencia que consultar.";
const RAIL_NOT_STRIPE = "El riel activo no es Stripe: los pagos de este espacio no generan transferencias que cuadrar.";

export function mockPayments(decisions: readonly Decision[], policy: Policy, now: string): PaymentsOverview {
  const paid = decisions.filter((decision) => PAID.has(decision.status));
  return {
    rail: "simulated",
    base_currency: policy.base_currency,
    payments: paid.map(({ invoice_id, supplier_name, status, amount, currency, amount_base, execution }) => ({
      invoice_id,
      supplier_name,
      status,
      amount,
      currency,
      amount_base,
      execution: execution ?? null,
    })),
    stripe: {
      status: "not_applicable",
      message: RAIL_NOT_STRIPE,
      checked_at: now,
      complete: false,
      lines: [],
      recorded_total: 0,
      stripe_total: 0,
      difference: 0,
    },
    exportable: paid.length,
  };
}

export function mockStripeProof(decision: Decision, now: string): StripeProof {
  return {
    invoice_id: decision.invoice_id,
    status: "not_applicable",
    message: NOT_STRIPE,
    checked_at: now,
    transfer: null,
    checks: [],
    dashboard_url: null,
    raw: null,
  };
}
