import type { DecisionReceipt } from "@/lib/api/client";

const TAMPER_FACTOR = 10;

export interface Tampered {
  receipt: DecisionReceipt;
  from: string;
  to: string;
}

/** What an attacker would do with a receipt: make the payment ten times larger and leave the signatures alone. */
export function tamperAmount(receipt: DecisionReceipt): Tampered {
  const payment = receipt.body.payment;
  const from = payment?.amount ?? "0";
  const to = String(Number(from) * TAMPER_FACTOR);
  const body = { ...receipt.body, payment: payment ? { ...payment, amount: to } : payment };
  return { receipt: { ...receipt, body }, from, to };
}
