import { describe, expect, it } from "vitest";
import { DEMO, listItemOf } from "@/lib/api/mock/dataset";

const ITEMS = DEMO.items.map(listItemOf);
import { decisionsByDay, matchesFilter, statusTotals } from "./summarize";

describe("statusTotals", () => {
  it("adds base amounts for paid, held and pending decisions", () => {
    const totals = statusTotals(ITEMS);

    expect(totals.paid.count).toBe(DEMO.metrics.paid_auto);
    expect(totals.held.count).toBe(DEMO.metrics.hold);
    expect(totals.pending.count).toBe(DEMO.metrics.pending);
    expect(totals.paid.total).toBeCloseTo(DEMO.company.spent_auto_base, 2);
  });
});

describe("decisionsByDay", () => {
  it("counts each day's outcomes in Colombia time, in order", () => {
    const days = decisionsByDay(ITEMS);

    expect(days[0]).toEqual({ day: "2026-10-01", label: "1 oct", paid: 3, pending: 0, held: 0 });
    expect(days.reduce((sum, d) => sum + d.paid + d.pending + d.held, 0)).toBe(DEMO.items.length);
  });
});

describe("matchesFilter", () => {
  const [first] = ITEMS;

  it("finds by supplier or invoice id, ignoring accents and case", () => {
    expect(matchesFilter(first, "all", "andes")).toBe(true);
    expect(matchesFilter(first, "all", "f-001")).toBe(true);
    expect(matchesFilter(first, "all", "pixel")).toBe(false);
  });

  it("filters by status group", () => {
    expect(matchesFilter(first, "paid", "")).toBe(true);
    expect(matchesFilter(first, "pending", "")).toBe(false);
  });
});
