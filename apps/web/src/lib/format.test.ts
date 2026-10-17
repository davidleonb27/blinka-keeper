import { describe, expect, it } from "vitest";
import {
  formatCount,
  formatDate,
  formatDateTime,
  formatMoney,
  formatPercent,
  shortHash,
} from "./format";

describe("formatMoney", () => {
  it("groups thousands the es-CO way and prefixes the ISO code", () => {
    expect(formatMoney(4800, "USD")).toBe("USD 4.800");
    expect(formatMoney(26650000, "COP")).toBe("COP 26.650.000");
  });

  it("shows cents only for small amounts that have them", () => {
    expect(formatMoney(840.5, "USD")).toBe("USD 840,50");
    expect(formatMoney(1250.5, "USD")).toBe("USD 1.251");
    expect(formatMoney(840, "USD")).toBe("USD 840");
  });

  it("honours an explicit number of decimals", () => {
    expect(formatMoney(1250.5, "USD", { decimals: 2 })).toBe("USD 1.250,50");
  });

  it("renders a missing amount as a dash, never as zero", () => {
    expect(formatMoney(null, "USD")).toBe("—");
    expect(formatMoney(Number.NaN, "USD")).toBe("—");
  });

  it("marks an unknown currency instead of guessing one", () => {
    expect(formatMoney(2450000, null)).toBe("¿? 2.450.000");
  });
});

describe("formatPercent", () => {
  it("formats ratios with a non-breaking space before the sign", () => {
    expect(formatPercent(0.8571)).toBe("86 %");
    expect(formatPercent(0.8571, 1)).toBe("85,7 %");
  });

  it("says NO MEDIDO for a metric that was not measured", () => {
    expect(formatPercent(null)).toBe("NO MEDIDO");
  });
});

describe("dates", () => {
  it("formats an ISO date as day and short month in Spanish", () => {
    expect(formatDate("2026-10-16")).toBe("16 oct");
    expect(formatDate("2026-01-03T10:00:00Z")).toBe("3 ene");
  });

  it("formats a timestamp in Colombia time", () => {
    expect(formatDateTime("2026-10-16T14:05:00Z")).toBe("16 oct · 09:05");
  });

  it("renders a missing date as a dash", () => {
    expect(formatDate(null)).toBe("—");
  });
});

describe("small helpers", () => {
  it("groups counts", () => {
    expect(formatCount(12034)).toBe("12.034");
  });

  it("shortens a hash for display", () => {
    expect(shortHash("9f2c4e1ab7d03f5566e1")).toBe("9f2c4e1ab7…");
  });
});
