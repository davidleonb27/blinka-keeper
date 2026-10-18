import { describe, expect, it } from "vitest";
import { DEMO, listItemOf } from "@/lib/api/mock/dataset";
import { STATUS_META } from "@/lib/presentation";
import { decisionsCsv } from "./decisions-csv";

const ITEMS = DEMO.items.map(listItemOf);

describe("decisionsCsv", () => {
  const [header, ...lines] = decisionsCsv(ITEMS).trimEnd().split("\r\n");

  it("has one row per decision under the columns finance asks for", () => {
    expect(header).toBe("proveedor,numero,monto,moneda,estado,regla_decisiva,fecha,id_transferencia");
    expect(lines).toHaveLength(ITEMS.length);
  });

  it("writes the amount as a plain number and the date as ISO, so a spreadsheet reads them", () => {
    const paid = ITEMS.find((item) => item.decision.status === "paid_auto" && item.decision.amount !== null)!;
    const line = lines[ITEMS.indexOf(paid)];
    expect(line).toContain(`,${paid.decision.amount},${paid.decision.currency},${STATUS_META.paid_auto.label},`);
    expect(line).toContain(`,${paid.received_at.slice(0, 10)},`);
  });

  it("names the rule that decided a held invoice", () => {
    const held = ITEMS.find((item) => item.decision.status === "hold")!;
    const rule = held.decision.rules.find((r) => r.outcome === "hold")!;
    expect(lines[ITEMS.indexOf(held)]).toContain(`${rule.rule_id} ${rule.label}`);
  });

  it("quotes fields with commas, quotes or line breaks", () => {
    const [item] = ITEMS;
    const tricky = { ...item, decision: { ...item.decision, supplier_name: 'Acme, "la buena"\nSAS' } };
    expect(decisionsCsv([tricky])).toContain('"Acme, ""la buena""\nSAS"');
  });

  it("escapes text that a spreadsheet would run as a formula, and leaves numbers alone", () => {
    const [item] = ITEMS;
    for (const name of ['=HYPERLINK("http://x")', "+1", "-1+1", "@SUM(A1)", "\tcmd"]) {
      const evil = { ...item, invoice_number: name, decision: { ...item.decision, supplier_name: name, amount: -5 } };
      const [, line] = decisionsCsv([evil]).trimEnd().split("\r\n");
      const quoted = name.includes('"') ? `"'${name.replaceAll('"', '""')}"` : `'${name}`;
      expect(line.startsWith(`${quoted},${quoted},-5,`)).toBe(true);
    }
  });

  it("never leaves the transfer id blank: the rail's id, else the instruction's key, else «—»", () => {
    const paid = ITEMS.find((item) => item.decision.status === "paid_auto")!;
    const at = "2026-10-17T12:00:00Z";
    const instruction = { network: "ach", amount: 1, currency: "USD", beneficiary_name: "x", beneficiary_tax_id: "1",
      beneficiary_country: null, bank_name: "b", account_number: "1", reference: "r", idempotency_key: "pay-F-001" };
    const withExecution = (execution: object | null) => ({ ...paid, decision: { ...paid.decision, execution } }) as typeof paid;
    const transferOf = (item: typeof paid) => decisionsCsv([item]).trimEnd().split("\r\n")[1].split(",").at(-1);

    expect(transferOf(withExecution({ rail: "stripe_test", status: "executed", external_id: "tr_123", executed_at: at }))).toBe("tr_123");
    expect(transferOf(withExecution({ rail: "blinka_simulated", status: "simulated", executed_at: at, instruction }))).toBe("pay-F-001");
    expect(transferOf(withExecution({ rail: "simulated", status: "simulated", executed_at: at }))).toBe("—");
    expect(transferOf(withExecution(null))).toBe("—");
  });
});
