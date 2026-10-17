import { describe, expect, it } from "vitest";
import { DEMO, listItemOf } from "@/lib/api/mock/dataset";
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
    expect(line).toContain(`,${paid.decision.amount},${paid.decision.currency},Pagada,`);
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
});
