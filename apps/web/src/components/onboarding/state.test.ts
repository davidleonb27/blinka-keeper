import { describe, expect, it } from "vitest";
import { draftPolicy, INITIAL_ANSWERS, onboardingRequest, withProfile } from "./state";

describe("draftPolicy", () => {
  it("sends approvers with only a name, a role and an email: approvals are web only", () => {
    const answers = {
      ...INITIAL_ANSWERS,
      approvers: [{ name: " Ana Gómez ", role: "", email: "ana@cafe.co" }],
    };

    expect(draftPolicy(answers).approvers).toEqual([
      { name: "Ana Gómez", role: null, email: "ana@cafe.co" },
    ]);
  });
});

describe("onboardingRequest", () => {
  it("keeps the currency and country the person chose even when the proposed profile said otherwise", () => {
    const proposed = { company_name: "Papelería El Trigal", website: null, industry: null, country: null, base_currency: "USD", summary: null, likely_suppliers: [], suggested_rules_text: null, evidence_urls: [] };
    const request = onboardingRequest({ ...INITIAL_ANSWERS, companyName: "Papelería El Trigal", profile: proposed, country: "CO", currency: "COP" });

    expect(request.profile).toMatchObject({ country: "CO", base_currency: "COP" });
    expect(request.policy).toMatchObject({ base_currency: "COP", allowed_currencies: ["COP"] });
  });
});

describe("suggested rules", () => {
  it("never leaves blanks to fill: without a usable suggestion it writes a complete example in the company's currency", () => {
    const profile = { company_name: "Papelería El Trigal", website: null, industry: null, country: "CO", base_currency: "COP", summary: null, likely_suppliers: [], suggested_rules_text: null, evidence_urls: [] };
    const answers = withProfile({ ...INITIAL_ANSWERS, currency: "COP" }, profile);

    expect(answers.rulesText).not.toMatch(/\[|\]/);
    expect(answers.rulesText).toMatch(/\d/);
    expect(answers.rulesText).toMatch(/COP|pesos/);
  });
});
