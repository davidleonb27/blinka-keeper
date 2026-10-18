"use client";

import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useApi } from "@/components/providers/api-provider";
import { useHydrated } from "@/lib/hydration";
import type {
  ApprovalInput,
  CustodioApi,
  ChallengeInput,
  InvoiceInput,
  OnboardingRequest,
  ProfileRequest,
  ReconciliationView,
  ResolveInput,
  StatementInput,
} from "./client";
import type { Beneficiary, Policy } from "./contracts";
import { markTourStep } from "@/lib/tour";
import { browserWorkspaceStore, forgetFreshBlank, isFreshBlank, type WorkspaceStore } from "./workspace";

const CHALLENGE_POLL_MS = 5_000;

const queryKeys = {
  workspace: ["workspace"] as const,
  decisions: ["decisions"] as const,
  decision: (id: string) => ["decisions", id] as const,
  policy: ["policy"] as const,
  ledger: ["ledger"] as const,
  challenge: ["challenge-stats"] as const,
  trust: ["trust"] as const,
  schedule: ["schedule"] as const,
  payments: ["payments"] as const,
  stripeProof: (id: string) => ["payments", id, "stripe"] as const,
  reconciliations: ["reconciliations"] as const,
  reconciliation: (id: string) => ["reconciliations", id] as const,
};

const HYDRATING = "hydrating";

interface ClientQuery<T> {
  queryKey: QueryKey;
  queryFn: () => Promise<T>;
  enabled?: boolean;
  refetchInterval?: number;
}

/**
 * A query whose data exists only in the browser. The server prerenders every page without it, but a part of the page
 * that hydrates late (a Suspense boundary whose code arrives after the shell's) can find it already cached, render it
 * and break hydration (React #418). Until the component has hydrated it reads an empty, disabled key, so its first
 * render is the server's; right after, it reads the real key and shows the cached data at once.
 */
function useClientQuery<T>({ queryKey, enabled = true, ...options }: ClientQuery<T>) {
  const hydrated = useHydrated();
  return useQuery<T>({ ...options, queryKey: hydrated ? queryKey : [HYDRATING, ...queryKey], enabled: hydrated && enabled });
}

export function useHealth() {
  const api = useApi();
  return useClientQuery({ queryKey: ["health"], queryFn: () => api.health() });
}

export function useWorkspaceSummary() {
  const api = useApi();
  return useClientQuery({ queryKey: queryKeys.workspace, queryFn: () => api.getWorkspace() });
}

export function useDecisions() {
  const api = useApi();
  return useClientQuery({ queryKey: queryKeys.decisions, queryFn: () => api.listDecisions() });
}

export function useDecision(invoiceId: string | null) {
  const api = useApi();
  return useClientQuery({
    queryKey: queryKeys.decision(invoiceId ?? ""),
    queryFn: () => api.getDecision(invoiceId ?? ""),
    enabled: invoiceId !== null,
  });
}

export function usePolicy() {
  const api = useApi();
  return useClientQuery({ queryKey: queryKeys.policy, queryFn: () => api.getPolicy() });
}

export function useLedger() {
  const api = useApi();
  return useClientQuery({ queryKey: queryKeys.ledger, queryFn: () => api.getLedger() });
}

export function useTrust() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.trust, queryFn: () => api.getTrust() });
}

export function useSchedule() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.schedule, queryFn: () => api.getSchedule() });
}

export function usePayments() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.payments, queryFn: () => api.getPayments() });
}

/** Asked live each time the acta opens; the API keeps Stripe's answer a few seconds. */
export function useStripeProof(invoiceId: string, enabled: boolean) {
  const api = useApi();
  return useClientQuery({ queryKey: queryKeys.stripeProof(invoiceId), queryFn: () => api.getStripeProof(invoiceId), enabled });
}

export function useSimulateMonth() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({ mutationFn: () => api.simulateMonth(), onSuccess: invalidate });
}

export function useRunDuePayments() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({ mutationFn: () => api.runDuePayments(), onSuccess: invalidate });
}

export function useChallengeStats(pollMs = CHALLENGE_POLL_MS) {
  const api = useApi();
  return useClientQuery({
    queryKey: queryKeys.challenge,
    queryFn: () => api.getChallengeStats(),
    refetchInterval: pollMs,
  });
}

function useInvalidateWorkspace() {
  const client = useQueryClient();
  return () =>
    Promise.all(
      [
        queryKeys.workspace,
        queryKeys.decisions,
        queryKeys.ledger,
        queryKeys.policy,
        queryKeys.trust,
        queryKeys.schedule,
        queryKeys.payments,
      ].map((queryKey) =>
        client.invalidateQueries({ queryKey }),
      ),
    );
}

export function useHumanDecision(invoiceId: string) {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({
    mutationFn: ({ approve, input }: { approve: boolean; input: ApprovalInput }) =>
      approve ? api.approveDecision(invoiceId, input) : api.rejectDecision(invoiceId, input),
    onSuccess: invalidate,
  });
}

export function useRetryPayment(invoiceId: string) {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({ mutationFn: () => api.executePayment(invoiceId), onSuccess: invalidate });
}

export function useCompilePolicy() {
  const api = useApi();
  return useMutation({
    mutationFn: ({ text, base }: { text: string; base?: Policy }) => api.compilePolicy(text, base),
  });
}

export function useApplyPolicy() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({
    mutationFn: (policy: Policy) => api.applyPolicy(policy),
    onSuccess: () => {
      markTourStep("rule");
      return invalidate();
    },
  });
}

export function useAddSuppliers() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({ mutationFn: (beneficiaries: Beneficiary[]) => api.addSuppliers(beneficiaries), onSuccess: invalidate });
}

export function useVerifyLedger() {
  const api = useApi();
  return useMutation({ mutationFn: () => api.verifyLedger(), onSuccess: () => markTourStep("verify") });
}

export function useTamperDemo() {
  const api = useApi();
  return useMutation({ mutationFn: () => api.tamperDemo(), onSuccess: () => markTourStep("verify") });
}

export function useSubmitChallenge() {
  const api = useApi();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: ChallengeInput) => api.submitChallengeAttempt(input),
    onSuccess: () => {
      markTourStep("steal");
      return client.invalidateQueries({ queryKey: queryKeys.challenge });
    },
  });
}

export function useProposeProfile() {
  const api = useApi();
  return useMutation({ mutationFn: (input: ProfileRequest) => api.proposeProfile(input) });
}

export function useImportSuppliers() {
  const api = useApi();
  return useMutation({
    mutationFn: ({ file, currency }: { file: File; currency?: string }) => api.importSuppliers(file, currency),
  });
}

/** A blank workspace no company was set up in yet and nothing arrived to: the onboarding can use it as is. */
async function isUnusedBlank(api: CustodioApi): Promise<boolean> {
  try {
    const summary = await api.getWorkspace();
    return summary.mode === "blank" && summary.policy_version === 1 && summary.metrics.total === 0 && summary.pending_invoices === 0;
  } catch {
    return false; // no workspace yet, or it is gone: make one
  }
}

/**
 * The new company gets a blank workspace of its own (the visitor's demo keeps its invoices out of it); the browser
 * switches to it before the API sets it up, and back to the one it had if the API refuses the company. A blank
 * workspace this page already made for the onboarding (a visitor who came straight to /empezar) is used as is.
 */
export function useCompleteOnboarding(store: WorkspaceStore = browserWorkspaceStore) {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({
    mutationFn: async (request: OnboardingRequest) => {
      const previous = { workspace_id: store.read(), api_key: store.readApiKey() };
      const fresh =
        (previous.workspace_id !== null && isFreshBlank(previous.workspace_id)) || (await isUnusedBlank(api));
      if (!fresh) store.write(await api.createWorkspace("blank"));
      try {
        const result = await api.completeOnboarding(request);
        forgetFreshBlank(result.workspace.workspace_id);
        return result;
      } catch (error) {
        const { workspace_id, api_key } = previous;
        if (workspace_id && api_key) store.write({ workspace_id, api_key });
        throw error;
      }
    },
    onSuccess: invalidate,
  });
}

/** Receives one invoice; the summary refreshes so the panel counts it among those waiting to be decided. */
export function useUploadInvoice() {
  const api = useApi();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: InvoiceInput) => api.uploadInvoice(input),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.workspace }),
  });
}

export function useProcessInvoices() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({
    mutationFn: () => api.processInvoices(),
    onSuccess: () => {
      markTourStep("decide");
      return invalidate();
    },
  });
}

export function useReconciliations() {
  const api = useApi();
  return useClientQuery({ queryKey: queryKeys.reconciliations, queryFn: () => api.listReconciliations() });
}

export function useReconciliation(id: string | null) {
  const api = useApi();
  return useClientQuery({
    queryKey: queryKeys.reconciliation(id ?? ""),
    queryFn: () => api.getReconciliation(id ?? ""),
    enabled: id !== null,
  });
}

/** Keeps the reconciliation the API just answered, and refreshes the list and the ledger it wrote to. */
function useStoreReconciliation() {
  const client = useQueryClient();
  return (view: ReconciliationView) => {
    client.setQueryData(queryKeys.reconciliation(view.id), view);
    return Promise.all(
      [queryKeys.reconciliations, queryKeys.ledger].map((queryKey) => client.invalidateQueries({ queryKey })),
    );
  };
}

export function useReconcileStatement() {
  const api = useApi();
  const store = useStoreReconciliation();
  return useMutation({
    mutationFn: (input: StatementInput) => api.reconcileStatement(input),
    onSuccess: (view: ReconciliationView) => {
      markTourStep("reconcile");
      return store(view);
    },
  });
}

export function useResolveMovement(id: string) {
  const api = useApi();
  const store = useStoreReconciliation();
  return useMutation({ mutationFn: (input: ResolveInput) => api.resolveMovement(id, input), onSuccess: store });
}

export function useClosePeriod(id: string) {
  const api = useApi();
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ period, closedBy }: { period: string; closedBy: string }) => api.closePeriod(period, closedBy),
    onSuccess: () =>
      Promise.all(
        [queryKeys.reconciliation(id), queryKeys.reconciliations, queryKeys.ledger].map((queryKey) =>
          client.invalidateQueries({ queryKey }),
        ),
      ),
  });
}
