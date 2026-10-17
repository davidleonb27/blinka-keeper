import { describe, expect, it } from "vitest";
import { draftPolicy, INITIAL_ANSWERS, onboardingRequest, exampleRules, withCurrency, withProfile } from "./state";

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

describe("withCurrency", () => {
  it("moves the suggested numbers and example rules to the new currency, and keeps what the person typed", () => {
    const usd = { ...INITIAL_ANSWERS, currency: "USD", balance: "50000", reserve: "123", rulesText: exampleRules("USD") };

    const cop = withCurrency(usd, "COP");

    expect(cop).toMatchObject({ currency: "COP", balance: "200000000", reserve: "123", rulesText: exampleRules("COP") });
  });
});

describe("withCurrency and a proposed suggestion", () => {
  it("replaces rules the profile suggested in the old currency, untouched, with an example in the new one", () => {
    const suggested = "Nada sobre 500 dólares sin mi aprobación.";
    const usd = { ...INITIAL_ANSWERS, currency: "USD", rulesText: suggested, profile: { company_name: "x", website: null, industry: null, country: null, base_currency: "USD", summary: null, likely_suppliers: [], suggested_rules_text: suggested, evidence_urls: [] } };

    expect(withCurrency(usd, "COP").rulesText).toBe(exampleRules("COP"));
    expect(withCurrency({ ...usd, rulesText: "Mis reglas" }, "COP").rulesText).toBe("Mis reglas");
  });
});
