/**
 * Checking a Custodio receipt in the browser, with nothing but the public key: the same algorithm as the API's
 * `custodio.receipts.verify_receipt`. One Ed25519 signature covers the canonical body; a second one covers the SHA-256
 * of each field, which is how the check names the field that was altered.
 */
import { ed25519 } from "@noble/curves/ed25519.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { canonicalBytes, leaves } from "./canonical";
import { fieldLabel, spanishList, VERDICT_LABELS } from "./labels";

export const RECEIPT_FORMAT = "custodio-receipt/1";
export const ALGORITHM = "Ed25519";

export interface PublicReceiptKey {
  key_id: string;
  /** The raw 32 bytes, standard base64. */
  public_key: string;
}

export interface BrowserCheck {
  valid: boolean;
  message: string;
  keyId: string | null;
  invoiceId: string | null;
  verdict: string | null;
  alteredFields: string[];
  alteredLabels: string[];
}

interface Envelope {
  keyId: string;
  body: Record<string, unknown>;
  signature: Uint8Array;
  digests: Record<string, unknown>;
  digestsSignature: Uint8Array;
}

const NOT_A_RECEIPT = "Inválido: esto no tiene la forma de un recibo firmado de Custodio.";
const BAD_SIGNATURE = "Inválido: la firma no corresponde a este contenido ni a la clave de Custodio.";

export function fromBase64(text: unknown): Uint8Array | null {
  if (typeof text !== "string" || !/^[A-Za-z0-9+/]*={0,2}$/.test(text)) return null;
  try {
    return Uint8Array.from(atob(text), (char) => char.charCodeAt(0));
  } catch {
    return null;
  }
}

export function fieldDigests(body: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(leaves(body).map(([path, value]) => [path, bytesToHex(sha256(canonicalBytes(value)))]));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function parse(raw: unknown): Envelope | null {
  if (!isRecord(raw) || raw.format !== RECEIPT_FORMAT || raw.algorithm !== ALGORITHM) return null;
  const { key_id: keyId, body, field_digests: digests } = raw;
  const signature = fromBase64(raw.signature);
  const digestsSignature = fromBase64(raw.digests_signature);
  if (typeof keyId !== "string" || !isRecord(body) || !isRecord(digests) || !signature || !digestsSignature) return null;
  return { keyId, body, signature, digests, digestsSignature };
}

function verifies(publicKey: Uint8Array, signature: Uint8Array, value: unknown): boolean {
  try {
    return ed25519.verify(signature, canonicalBytes(value), publicKey, { zip215: false });
  } catch {
    return false;
  }
}

function textAt(body: Record<string, unknown>, section: string, name: string): string | null {
  const part = body[section];
  const value = isRecord(part) ? part[name] : undefined;
  return typeof value === "string" ? value : null;
}

function alteredFields(envelope: Envelope, publicKey: Uint8Array): string[] {
  if (!verifies(publicKey, envelope.digestsSignature, envelope.digests)) return [];
  const now = fieldDigests(envelope.body);
  const paths = new Set([...Object.keys(now), ...Object.keys(envelope.digests)]);
  return [...paths].filter((path) => now[path] !== envelope.digests[path]).sort();
}

const EMPTY = { keyId: null, invoiceId: null, verdict: null, alteredFields: [], alteredLabels: [] };

export function verifyReceiptInBrowser(raw: unknown, key: PublicReceiptKey): BrowserCheck {
  try {
    return check(raw, key);
  } catch {
    // a body nested past the stack: no receipt is spelled like that
    return { ...EMPTY, valid: false, message: NOT_A_RECEIPT };
  }
}

function check(raw: unknown, key: PublicReceiptKey): BrowserCheck {
  const envelope = parse(raw);
  const publicKey = fromBase64(key.public_key);
  if (!envelope || !publicKey) return { ...EMPTY, valid: false, message: NOT_A_RECEIPT };
  if (envelope.keyId !== key.key_id) {
    const message = `Inválido: el recibo dice estar firmado con la clave ${envelope.keyId} y la clave de Custodio es ${key.key_id}.`;
    return { ...EMPTY, keyId: envelope.keyId, valid: false, message };
  }
  const seen = { ...EMPTY, keyId: key.key_id, invoiceId: textAt(envelope.body, "invoice", "id") };
  if (verifies(publicKey, envelope.signature, envelope.body) && envelope.body.key_id === key.key_id) {
    const verdict = textAt(envelope.body, "decision", "verdict");
    const label = VERDICT_LABELS[verdict ?? ""] ?? "sin decisión";
    const message = `Válido: firmado por Custodio con la clave ${key.key_id}. La decisión fue «${label}».`;
    return { ...seen, valid: true, verdict, message };
  }
  const altered = alteredFields(envelope, publicKey);
  if (altered.length === 0) return { ...seen, valid: false, message: BAD_SIGNATURE };
  const labels = [...new Set(altered.map((path) => fieldLabel(path, envelope.body)))];
  const message =
    labels.length === 1
      ? `Inválido: el campo ${labels[0]} fue alterado después de firmarse.`
      : `Inválido: los campos ${spanishList(labels)} fueron alterados después de firmarse.`;
  return { ...seen, valid: false, message, alteredFields: altered, alteredLabels: labels };
}
