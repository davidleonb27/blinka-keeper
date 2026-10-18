import { describe, expect, it } from "vitest";
import { canonicalJson, leaves } from "./canonical";
import golden from "./golden-receipt.json";
import { keyFromSeed, signBody } from "./sign";
import { verifyReceiptInBrowser } from "./verify";

const SEED = Uint8Array.from({ length: 32 }, (_, index) => index);
const OTHER_SEED = Uint8Array.from({ length: 32 }, (_, index) => index + 1);

function copy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function alter(receipt: typeof golden.receipt, path: string): typeof golden.receipt {
  const altered = copy(receipt);
  const parts = path.split(".");
  const last = parts.pop() as string;
  let target: Record<string, unknown> | unknown[] = altered.body as unknown as Record<string, unknown>;
  for (const part of parts) target = (target as Record<string, unknown>)[part] as Record<string, unknown>;
  const record = target as Record<string, unknown>;
  const value = record[last];
  record[last] = typeof value === "boolean" ? !value : typeof value === "number" ? value + 1 : value === null ? "x" : `${String(value)}0`;
  return altered;
}

describe("receipts checked in the browser", () => {
  it("writes the very canonical body the API signs, accents included", () => {
    expect(canonicalJson(golden.receipt.body)).toBe(golden.canonical_body);
  });

  it("accepts the receipt the API signed and says the decision", () => {
    const check = verifyReceiptInBrowser(golden.receipt, golden.key);

    expect(check.valid).toBe(true);
    expect(check.verdict).toBe("pay");
    expect(check.message).toBe(`Válido: firmado por Custodio con la clave ${golden.key.key_id}. La decisión fue «Pagar».`);
  });

  it("signs byte for byte like the API with the same key", () => {
    expect(keyFromSeed(SEED)).toEqual({ key_id: golden.key.key_id, public_key: golden.key.public_key });
    expect(signBody(golden.receipt.body, SEED)).toEqual(golden.receipt);
  });

  it.each(Object.keys(golden.receipt.field_digests))("catches and names an altered %s", (path) => {
    const check = verifyReceiptInBrowser(alter(golden.receipt, path), golden.key);

    expect(check.valid).toBe(false);
    expect(check.alteredFields).toEqual([path]);
    expect(check.message).toContain(check.alteredLabels[0]);
  });

  it("says «el campo monto fue alterado» for the amount", () => {
    const check = verifyReceiptInBrowser(alter(golden.receipt, "payment.amount"), golden.key);

    expect(check.message).toBe("Inválido: el campo monto fue alterado después de firmarse.");
  });

  it("refuses a receipt signed with another key, even if it claims ours", () => {
    const stranger = keyFromSeed(OTHER_SEED);
    const forged = signBody({ ...golden.receipt.body, key_id: stranger.key_id }, OTHER_SEED);
    const claimed = { ...signBody(golden.receipt.body, OTHER_SEED), key_id: golden.key.key_id };

    expect(verifyReceiptInBrowser(forged, golden.key).message).toContain(stranger.key_id);
    expect(verifyReceiptInBrowser(claimed, golden.key).valid).toBe(false);
    expect(verifyReceiptInBrowser(golden.receipt, stranger).valid).toBe(false);
  });

  it("does not fall for a field edited together with its digest", () => {
    const altered = alter(golden.receipt, "payment.amount");
    const digest = signBody(altered.body, OTHER_SEED).field_digests;

    const check = verifyReceiptInBrowser({ ...altered, field_digests: digest }, golden.key);

    expect(check.valid).toBe(false);
    expect(check.alteredFields).toEqual([]);
  });

  it.each([null, [], "recibo", {}, { ...golden.receipt, signature: "%%" }, { ...golden.receipt, algorithm: "RSA" }])(
    "says when something is not a receipt (%#)",
    (raw) => {
      expect(verifyReceiptInBrowser(raw, golden.key).message).toBe(
        "Inválido: esto no tiene la forma de un recibo firmado de Custodio.",
      );
    },
  );

  it("ignores key order and whitespace", () => {
    const shuffled = JSON.parse(JSON.stringify(Object.fromEntries(Object.entries(golden.receipt.body).reverse()), null, 4));

    expect(canonicalJson(shuffled)).toBe(golden.canonical_body);
    expect(leaves({ a: {}, b: [] })).toEqual([
      ["a", {}],
      ["b", []],
    ]);
  });
});
