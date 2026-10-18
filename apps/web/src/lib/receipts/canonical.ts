/**
 * The canonical JSON Custodio signs: keys sorted, no spaces, accents written as they are. It is the same text Python's
 * `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` writes for the values a receipt holds
 * (strings, integers, booleans, null, lists and objects).
 */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => item !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

const encoder = new TextEncoder();

export function canonicalBytes(value: unknown): Uint8Array {
  return encoder.encode(canonicalJson(value));
}

/** One path per field: "payment.amount", "rules.3.outcome". An empty object or list counts as one field. */
export function leaves(value: unknown, prefix = ""): [string, unknown][] {
  if (Array.isArray(value) && value.length > 0) {
    return value.flatMap((item, index) => leaves(item, `${prefix}.${index}`));
  }
  if (value !== null && typeof value === "object" && Object.keys(value).length > 0) {
    return Object.entries(value as Record<string, unknown>).flatMap(([key, item]) =>
      leaves(item, prefix ? `${prefix}.${key}` : key),
    );
  }
  return [[prefix, value]];
}
