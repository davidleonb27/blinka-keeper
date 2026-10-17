import { describe, expect, it } from "vitest";
import type { RedTeamEvent } from "../contracts";
import { createMockClient } from "./mock-client";

const instant = { latencyMs: 0 };

describe("mock client", () => {
  it("serves the prototype company with twelve rules per decision", async () => {
    const api = createMockClient(instant);
    const workspace = await api.getWorkspace();
    const decisions = await api.listDecisions();

    expect(workspace.company_name).toBe("Cobalto Labs, Inc.");
    expect(workspace.metrics.improper_payments).toBe(0);
    expect(decisions).toHaveLength(workspace.metrics.total);
    expect(decisions.every((item) => item.decision.rules.length === 12)).toBe(true);
  });

  it("pays an approved invoice and records it in the ledger", async () => {
    const api = createMockClient(instant);
    const before = await api.getLedger();

    const decision = await api.approveDecision("F-015", { approver: "Ana Gómez" });

    expect(decision.status).toBe("paid_human");
    expect(decision.approval?.approver).toBe("Ana Gómez");
    expect((await api.getLedger()).length).toBe(before.length + 1);
    expect((await api.verifyLedger()).valid).toBe(true);
  });

  it("rejects without touching the balance", async () => {
    const api = createMockClient(instant);
    const { balance } = await api.getWorkspace();

    const decision = await api.rejectDecision("F-022", { approver: "Tomás Rivera" });

    expect(decision.status).toBe("rejected");
    expect((await api.getWorkspace()).balance).toBe(balance);
  });

  it("refuses to approve something that is not pending", async () => {
    const api = createMockClient(instant);
    await expect(api.approveDecision("F-001", { approver: "Ana Gómez" })).rejects.toThrow(
      /no espera aprobación/,
    );
  });

  it("compiles a threshold sentence into a policy change with its quote", async () => {
    const api = createMockClient(instant);
    const proposal = await api.compilePolicy("Nada sobre 3.000 USD sin que lo apruebe Ana");

    expect(proposal.changes).toEqual([
      expect.objectContaining({ field: "approval_threshold", before: 5000, after: 3000 }),
    ]);
    expect(proposal.proposed.approval_threshold).toBe(3000);
    expect(proposal.simulation?.changed.length).toBeGreaterThan(0);
  });

  it("returns what it did not understand instead of guessing", async () => {
    const api = createMockClient(instant);
    const proposal = await api.compilePolicy("Págale primero a los que me caen bien");

    expect(proposal.changes).toEqual([]);
    expect(proposal.unsupported).toEqual(["Págale primero a los que me caen bien"]);
  });

  it("shows a tampered copy breaking at the altered entry", async () => {
    const api = createMockClient(instant);
    const result = await api.tamperDemo();

    expect(result.verification.valid).toBe(false);
    expect(result.verification.first_broken_seq).toBe(result.tampered_seq);
    expect((await api.verifyLedger()).valid).toBe(true);
  });

  it("streams red-team rounds ending in a summary with zero improper payments", async () => {
    const api = createMockClient(instant);
    const events: RedTeamEvent[] = [];

    await api.runRedTeam({ rounds: 3 }, (event) => events.push(event));

    expect(events.filter((e) => e.type === "verdict")).toHaveLength(3);
    expect(events.filter((e) => e.type === "verdict").every((e) => e.caught)).toBe(true);
    expect(events.at(-1)?.type).toBe("summary");
  });

  it("proposes a profile that adapts to the company it is given", async () => {
    const api = createMockClient(instant);
    const profile = await api.proposeProfile({
      company_name: "Café La Montaña",
      website: "https://cafelamontana.co",
    });

    expect(profile.company_name).toBe("Café La Montaña");
    expect(profile.country).toBe("CO");
    expect(profile.base_currency).toBe("COP");
    expect(profile.suggested_rules_text).toBeTruthy();
  });
});
