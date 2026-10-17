import type { LedgerEntry, LedgerKind, LedgerVerification } from "../contracts";

const GENESIS_HASH = "0".repeat(64);

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const fields = Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`);
    return `{${fields.join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

type EntryBody = Pick<LedgerEntry, "seq" | "at" | "kind" | "subject_id" | "payload">;

function hashOf(prevHash: string, body: EntryBody): Promise<string> {
  const { seq, at, kind, subject_id, payload } = body;
  return sha256Hex(prevHash + canonicalJson({ seq, at, kind, subject_id, payload }));
}

export async function appendEntry(
  ledger: readonly LedgerEntry[],
  event: { kind: LedgerKind; subject_id: string | null; payload: Record<string, unknown>; at: string },
): Promise<LedgerEntry> {
  const prevHash = ledger.at(-1)?.hash ?? GENESIS_HASH;
  const body: EntryBody = { seq: ledger.length + 1, ...event };
  return { ...body, prev_hash: prevHash, hash: await hashOf(prevHash, body) };
}

export async function verifyChain(ledger: readonly LedgerEntry[]): Promise<LedgerVerification> {
  let prevHash = GENESIS_HASH;
  for (const entry of ledger) {
    const intact = entry.prev_hash === prevHash && (await hashOf(prevHash, entry)) === entry.hash;
    if (!intact) {
      return { valid: false, length: ledger.length, first_broken_seq: entry.seq, head_hash: null };
    }
    prevHash = entry.hash;
  }
  return { valid: true, length: ledger.length, first_broken_seq: null, head_hash: ledger.at(-1)?.hash ?? null };
}
