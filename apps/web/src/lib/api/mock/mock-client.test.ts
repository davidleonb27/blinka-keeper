import { describe, expect, it } from "vitest";
import type { RedTeamEvent } from "../contracts";
import raw from "./demo-dataset.json";
import { createMockClient } from "./mock-client";

const instant = { latencyMs: 0 };

async function processedDemo() {
  const api = createMockClient(instant);
  await api.processInvoices();
  return api;
}

describe("mock client", () => {
  it("starts like a fresh API demo workspace: invoices received, nothing decided yet", async () => {
    const api = createMockClient(instant);
    const workspace = await api.getWorkspace();

    expect(workspace.company_name).toBe("Cobalto Labs, Inc.");
    expect(workspace.pending_invoices).toBeGreaterThan(0);
    expect(workspace.metrics.total).toBe(0);
    expect(workspace.audit).toEqual({ agrees: true, checked: 0, improper_payments: 0, findings: [] });
    expect(await api.listDecisions()).toEqual([]);
  });

  it("decides every pending invoice when they are processed, with twelve rules each", async () => {
    const api = createMockClient(instant);
    const { pending_invoices: pending } = await api.getWorkspace();

    const outcome = await api.processInvoices();
    const workspace = await api.getWorkspace();
    const decisions = await api.listDecisions();

    expect(outcome.batch.decisions).toHaveLength(pending);
    expect(outcome.vetoed).toEqual([]);
    expect(workspace.pending_invoices).toBe(0);
    expect(workspace.metrics.improper_payments).toBe(0);
    expect(workspace.audit.checked).toBe(workspace.metrics.paid_auto);
    expect(decisions).toHaveLength(workspace.metrics.total);
    expect(decisions.every((item) => item.decision.rules.length === 12)).toBe(true);
    expect((await api.verifyLedger()).valid).toBe(true);
  });

  it("serves an acta with the invoice as read and the ledger entries about it", async () => {
    const api = await processedDemo();

    const acta = await api.getDecision("F-001");

    expect(acta.decision.invoice_id).toBe("F-001");
    expect(acta.invoice).toMatchObject({ id: "F-001", status: "decided", read_ok: true });
    expect(acta.ledger.map((entry) => entry.subject_id)).toEqual(["F-001"]);
  });

  it("carries no trace of a messaging channel for approvals", () => {
    expect(JSON.stringify(raw).toLowerCase().includes("telegram")).toBe(false);
  });

  it("pays an approved invoice and records it in the ledger", async () => {
    const api = await processedDemo();
    const before = await api.getLedger();

    const decision = await api.approveDecision("F-015", { approver: "Ana Gómez" });

    expect(decision.status).toBe("paid_human");
    expect(decision.approval?.approver).toBe("Ana Gómez");
    expect((await api.getLedger()).length).toBe(before.length + 1);
    expect((await api.verifyLedger()).valid).toBe(true);
  });

  it("pays on the simulated rail and says so in health", async () => {
    const api = await processedDemo();

    const approved = await api.approveDecision("F-015", { approver: "Ana Gómez" });
    const paid = (await api.getDecision("F-001")).decision;

    expect((await api.health()).payment_rail).toBe("simulated");
    expect(approved.execution?.status).toBe("simulated");
    expect(paid.execution?.rail).toBe("simulated");
  });

  it("returns an executed payment unchanged and refuses to execute an unpaid one", async () => {
    const api = await processedDemo();
    const paid = (await api.getDecision("F-001")).decision;

    expect(await api.executePayment("F-001")).toEqual(paid);
    await expect(api.executePayment("F-020")).rejects.toThrow();
  });

  it("rejects without touching the balance", async () => {
    const api = await processedDemo();
    const { balance } = await api.getWorkspace();

    const decision = await api.rejectDecision("F-022", { approver: "Tomás Rivera" });

    expect(decision.status).toBe("rejected");
    expect((await api.getWorkspace()).balance).toBe(balance);
  });

  it("refuses to approve something that is not pending", async () => {
    const api = await processedDemo();
    await expect(api.approveDecision("F-001", { approver: "Ana Gómez" })).rejects.toThrow(
      /no espera aprobación/,
    );
  });

  it("compiles a threshold sentence into a policy change with its quote", async () => {
    const api = await processedDemo();
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

  it("compiles against a draft without simulating it, like the API", async () => {
    const api = createMockClient(instant);
    const draft = await api.getPolicy();

    const proposal = await api.compilePolicy("Nada sobre 3.000 USD sin que lo apruebe Ana", draft);

    expect(proposal.proposed.approval_threshold).toBe(3000);
    expect(proposal.simulation).toBeNull();
  });

  it("shows a tampered copy breaking at the altered entry while the real one stays valid", async () => {
    const api = await processedDemo();
    const result = await api.tamperDemo();

    expect(result.altered_field).toBe("payload");
    expect(result.tampered.valid).toBe(false);
    expect(result.tampered.first_broken_seq).toBe(result.altered_seq);
    expect(result.real.valid).toBe(true);
    expect((await api.verifyLedger()).valid).toBe(true);
  });

  it("completes onboarding on a blank workspace and simulates one agreed invoice per supplier", async () => {
    const api = createMockClient(instant);
    await api.createWorkspace("blank");
    const policy = await api.getPolicy();
    const supplier = (await api.importSuppliers(new File(["x"], "lista.pdf"))).beneficiaries[0];

    const result = await api.completeOnboarding({
      profile: await api.proposeProfile({ company_name: "Café La Montaña", website: null }),
      policy,
      suppliers: [supplier],
      opening_balance: 50_000_000,
    });

    expect(result.workspace.company_name).toBe("Café La Montaña");
    expect(result.workspace.balance).toBe(50_000_000);
    expect(result.workspace.metrics.total).toBe(0);
    expect(result.first_week.decisions.map((d) => d.supplier_name)).toEqual([supplier.name]);
    expect(await api.listDecisions()).toEqual([]);
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
