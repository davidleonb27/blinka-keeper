/**
 * Signed receipts in the in-memory demo: the same format and the same check as the API, with a demo key that is fixed
 * and public (it only signs this browser's made-up company).
 */
import { keyFromSeed, signBody } from "../../receipts/sign";
import { verifyReceiptInBrowser } from "../../receipts/verify";
import type { Acta, DecisionReceipt, ReceiptBody, ReceiptCheck, ReceiptKey } from "../client";
import type { Decision } from "../contracts";

const DEMO_SEED = new TextEncoder().encode("custodio-demo-receipts-key-32b!!");
const SPKI_ED25519_PREFIX = "MCowBQYDK2VwAyEA"; // DER header of an Ed25519 SubjectPublicKeyInfo, in base64
const READ_FIELDS = [
  "supplier_name",
  "supplier_tax_id",
  "invoice_number",
  "issue_date",
  "due_date",
  "amount",
  "currency",
  "bank_name",
  "account_number",
] as const;
const VERDICTS: Record<Decision["status"], ReceiptBody["decision"]["verdict"]> = {
  paid_auto: "pay",
  paid_human: "pay",
  hold: "hold",
  pending_approval: "escalate",
  rejected: "reject",
};
const LAST_DIGITS = 4;

const demoKey = keyFromSeed(DEMO_SEED);

export const MOCK_RECEIPT_KEY: ReceiptKey = {
  format: "custodio-receipt/1",
  algorithm: "Ed25519",
  ...demoKey,
  public_key_pem: `-----BEGIN PUBLIC KEY-----\n${SPKI_ED25519_PREFIX}${demoKey.public_key}\n-----END PUBLIC KEY-----\n`,
};

function text(value: unknown): string {
  return value === null || value === undefined ? "0" : String(value);
}

function payment(decision: Decision, acta: Acta, baseCurrency: string): ReceiptBody["payment"] {
  if (VERDICTS[decision.status] !== "pay") return null;
  const account = acta.invoice.extraction.account_number.value;
  return {
    beneficiary_id: decision.beneficiary_id,
    beneficiary_name: decision.supplier_name ?? "",
    account_last4: account ? account.slice(-LAST_DIGITS) : null,
    account_sha256: null,
    amount: text(decision.amount ?? decision.amount_base),
    currency: decision.currency,
    amount_base: text(decision.amount_base),
    base_currency: baseCurrency,
    rail: decision.execution?.rail ?? null,
    external_id: decision.execution?.external_id ?? null,
  };
}

export function mockReceipt(acta: Acta, workspaceId: string, baseCurrency: string): DecisionReceipt {
  const { decision, invoice } = acta;
  const entry = acta.ledger.at(-1);
  const body: ReceiptBody = {
    format: "custodio-receipt/1",
    key_id: demoKey.key_id,
    workspace_id: workspaceId,
    issued_at: entry?.at ?? invoice.received_at,
    invoice: {
      id: invoice.id,
      number: invoice.extraction.invoice_number.value,
      received_at: invoice.received_at,
      source: invoice.extraction.source,
      document_id: invoice.document_id,
      document_sha256: null,
    },
    reading: Object.fromEntries(
      READ_FIELDS.map((name) => [
        name,
        { value: invoice.extraction[name].value, verified: invoice.extraction[name].verified ?? false },
      ]),
    ),
    rules: decision.rules.map((rule) => ({ rule_id: rule.rule_id, outcome: rule.outcome })),
    policy: { version: 1, sha256: null, ledger_seq: null, ledger_hash: null },
    decision: {
      verdict: VERDICTS[decision.status],
      status: decision.status,
      agent_verdict: decision.agent_verdict,
      approved_by: decision.approval?.approver ?? null,
    },
    payment: payment(decision, acta, baseCurrency),
    ledger: { seq: entry?.seq ?? 0, hash: entry?.hash ?? "0".repeat(64), kind: entry?.kind ?? "decision" },
  };
  return signBody(body, DEMO_SEED);
}

export function mockCheck(raw: unknown): ReceiptCheck {
  const check = verifyReceiptInBrowser(raw, MOCK_RECEIPT_KEY);
  return {
    valid: check.valid,
    message: check.message,
    key_id: check.keyId,
    invoice_id: check.invoiceId,
    verdict: check.verdict as ReceiptCheck["verdict"],
    altered_fields: check.alteredFields,
    altered_labels: check.alteredLabels,
  };
}
