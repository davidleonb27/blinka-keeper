import { describe, expect, it } from "vitest";
import { draftPolicy, INITIAL_ANSWERS } from "./state";

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
