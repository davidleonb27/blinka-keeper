/** Signing a receipt body the way the API does. Only the in-memory demo (mock client) and the tests sign in a browser. */
import { ed25519 } from "@noble/curves/ed25519.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { canonicalBytes } from "./canonical";
import { ALGORITHM, fieldDigests, RECEIPT_FORMAT } from "./verify";

const KEY_ID_HEX_CHARS = 16;

function toBase64(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes));
}

export function keyFromSeed(seed: Uint8Array): { key_id: string; public_key: string } {
  const publicKey = ed25519.getPublicKey(seed);
  return { key_id: `cust-${bytesToHex(sha256(publicKey)).slice(0, KEY_ID_HEX_CHARS)}`, public_key: toBase64(publicKey) };
}

export function signBody<B extends { key_id: string }>(body: B, seed: Uint8Array) {
  const digests = fieldDigests(body as unknown as Record<string, unknown>);
  return {
    format: RECEIPT_FORMAT,
    algorithm: ALGORITHM,
    key_id: body.key_id,
    body,
    signature: toBase64(ed25519.sign(canonicalBytes(body), seed)),
    field_digests: digests,
    digests_signature: toBase64(ed25519.sign(canonicalBytes(digests), seed)),
  } as const;
}
