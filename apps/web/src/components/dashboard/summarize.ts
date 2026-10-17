/** Aggregations of what the API already decided, for display. */
import type { DecisionListItem } from "@/lib/api/client";
import type { DecisionStatus } from "@/lib/api/contracts";
import { normalize } from "@/lib/text";
import { companyDay, formatDate } from "@/lib/format";

export type StatusFilter = "all" | "paid" | "held" | "pending" | "rejected";

const FILTER_STATUSES: Record<Exclude<StatusFilter, "all">, DecisionStatus[]> = {
  paid: ["paid_auto", "paid_human"],
  held: ["hold"],
  pending: ["pending_approval"],
  rejected: ["rejected"],
};

export interface Total {
  count: number;
  total: number;
}

function totalFor(items: DecisionListItem[], statuses: DecisionStatus[]): Total {
  const matching = items.filter((item) => statuses.includes(item.decision.status));
  return {
    count: matching.length,
    total: matching.reduce((sum, item) => sum + (item.decision.amount_base ?? 0), 0),
  };
}

export function statusTotals(items: DecisionListItem[]): Record<"paid" | "held" | "pending", Total> {
  return {
    paid: totalFor(items, FILTER_STATUSES.paid),
    held: totalFor(items, FILTER_STATUSES.held),
    pending: totalFor(items, FILTER_STATUSES.pending),
  };
}

export interface DayCounts {
  day: string;
  label: string;
  paid: number;
  pending: number;
  held: number;
}

const DAY_BUCKET: Partial<Record<DecisionStatus, "paid" | "pending" | "held">> = {
  paid_auto: "paid",
  paid_human: "paid",
  pending_approval: "pending",
  hold: "held",
  rejected: "held",
};

export function decisionsByDay(items: DecisionListItem[]): DayCounts[] {
  const days = new Map<string, DayCounts>();
  for (const { decision, received_at } of items) {
    const day = companyDay(received_at);
    const counts = days.get(day) ?? { day, label: formatDate(day), paid: 0, pending: 0, held: 0 };
    const bucket = DAY_BUCKET[decision.status];
    if (bucket) counts[bucket] += 1;
    days.set(day, counts);
  }
  return [...days.values()].sort((a, b) => a.day.localeCompare(b.day));
}

export function matchesFilter(item: DecisionListItem, filter: StatusFilter, query: string): boolean {
  const { decision } = item;
  if (filter !== "all" && !FILTER_STATUSES[filter].includes(decision.status)) return false;
  const needle = normalize(query.trim());
  if (!needle) return true;
  return normalize(`${decision.supplier_name ?? ""} ${decision.invoice_id}`).includes(needle);
}
