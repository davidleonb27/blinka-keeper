import { EXTRACTED_FIELD_NAMES, type ExtractedFieldName, type ExtractedInvoice } from "@/lib/api/contracts";

export interface Segment {
  text: string;
  fields: ExtractedFieldName[];
}

interface Span {
  start: number;
  end: number;
  fields: ExtractedFieldName[];
}

function evidenceSpans(extraction: ExtractedInvoice): Span[] {
  const byRange = new Map<string, Span>();
  for (const field of EXTRACTED_FIELD_NAMES) {
    const evidence = extraction[field].evidence;
    if (evidence?.char_start == null || evidence.char_end == null) continue;
    const key = `${evidence.char_start}:${evidence.char_end}`;
    const span = byRange.get(key) ?? { start: evidence.char_start, end: evidence.char_end, fields: [] };
    span.fields.push(field);
    byRange.set(key, span);
  }
  return [...byRange.values()].sort((a, b) => a.start - b.start);
}

/** Splits the visible text into plain and quoted runs. Overlapping quotes keep the earliest. */
export function documentSegments(extraction: ExtractedInvoice): Segment[] {
  const text = extraction.visible_text;
  const segments: Segment[] = [];
  let cursor = 0;
  for (const span of evidenceSpans(extraction)) {
    if (span.start < cursor || span.end > text.length) continue;
    if (span.start > cursor) segments.push({ text: text.slice(cursor, span.start), fields: [] });
    segments.push({ text: text.slice(span.start, span.end), fields: span.fields });
    cursor = span.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), fields: [] });
  return segments;
}
