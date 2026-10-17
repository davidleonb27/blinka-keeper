import { describe, expect, it } from "vitest";
import { DEMO } from "@/lib/api/mock/dataset";
import { planAdditions, supplierFromForm } from "./additions";

const POLICY = DEMO.policy;
const [KNOWN] = POLICY.beneficiaries;
const NEW = supplierFromForm(
  { name: "Panadería La Espiga SAS", tax_id: "900.777.123-4", bank_name: "Bancolombia", account_number: "4455 6677" },
  "COP",
);

describe("supplierFromForm", () => {
  it("builds a registered, allowed supplier with an id from its tax id", () => {
    expect(NEW).toMatchObject({
      id: "B-9007771234",
      name: "Panadería La Espiga SAS",
      tax_id: "900.777.123-4",
      bank_name: "Bancolombia",
      account_number: "4455 6677",
      currency: "COP",
      allowed: true,
    });
  });
});

describe("planAdditions", () => {
  it("adds suppliers the policy does not have yet", () => {
    expect(planAdditions(POLICY, [NEW])).toEqual({ added: [NEW], skipped: [] });
  });

  it("never touches a supplier already registered, even with other bank details: that change is verified out of band", () => {
    const changed = { ...KNOWN, id: "B-otro", account_number: "000-999", name: KNOWN.name.toUpperCase() };
    const plan = planAdditions(POLICY, [changed]);
    expect(plan.added).toEqual([]);
    expect(plan.skipped).toEqual([
      { name: changed.name, reason: expect.stringContaining("Ya está registrado") as unknown as string },
    ]);
  });

  it("skips the same supplier twice in one batch and rows with missing data", () => {
    const blank = supplierFromForm({ name: "Sin cuenta SAS", tax_id: "123", bank_name: "Davivienda", account_number: " " }, "COP");
    const plan = planAdditions(POLICY, [NEW, { ...NEW }, blank]);
    expect(plan.added).toEqual([NEW]);
    expect(plan.skipped.map((s) => s.name)).toEqual([NEW.name, "Sin cuenta SAS"]);
  });

  it("gives a new supplier an id no existing one has", () => {
    const clash = { ...NEW, id: KNOWN.id };
    expect(planAdditions(POLICY, [clash]).added[0].id).not.toBe(KNOWN.id);
  });
});
