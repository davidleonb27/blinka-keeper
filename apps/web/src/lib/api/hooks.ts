"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/components/providers/api-provider";
import type {
  ApprovalInput,
  ChallengeInput,
  OnboardingRequest,
  ProfileRequest,
  ReconciliationView,
  ResolveInput,
  StatementInput,
} from "./client";
import type { Policy } from "./contracts";
import { browserWorkspaceStore, type WorkspaceStore } from "./workspace";

const CHALLENGE_POLL_MS = 5_000;

const queryKeys = {
  workspace: ["workspace"] as const,
  decisions: ["decisions"] as const,
  decision: (id: string) => ["decisions", id] as const,
  policy: ["policy"] as const,
  ledger: ["ledger"] as const,
  challenge: ["challenge-stats"] as const,
  reconciliations: ["reconciliations"] as const,
  reconciliation: (id: string) => ["reconciliations", id] as const,
};

export function useHealth() {
  const api = useApi();
  return useQuery({ queryKey: ["health"], queryFn: () => api.health() });
}

export function useWorkspaceSummary() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.workspace, queryFn: () => api.getWorkspace() });
}

export function useDecisions() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.decisions, queryFn: () => api.listDecisions() });
}

export function useDecision(invoiceId: string | null) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.decision(invoiceId ?? ""),
    queryFn: () => api.getDecision(invoiceId ?? ""),
    enabled: invoiceId !== null,
  });
}

export function usePolicy() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.policy, queryFn: () => api.getPolicy() });
}

export function useLedger() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.ledger, queryFn: () => api.getLedger() });
}

export function useChallengeStats() {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.challenge,
    queryFn: () => api.getChallengeStats(),
    refetchInterval: CHALLENGE_POLL_MS,
  });
}

function useInvalidateWorkspace() {
  const client = useQueryClient();
  return () =>
    Promise.all(
      [queryKeys.workspace, queryKeys.decisions, queryKeys.ledger, queryKeys.policy].map((queryKey) =>
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
  return useMutation({ mutationFn: (policy: Policy) => api.applyPolicy(policy), onSuccess: invalidate });
}

export function useVerifyLedger() {
  const api = useApi();
  return useMutation({ mutationFn: () => api.verifyLedger() });
}

export function useTamperDemo() {
  const api = useApi();
  return useMutation({ mutationFn: () => api.tamperDemo() });
}

export function useSubmitChallenge() {
  const api = useApi();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: ChallengeInput) => api.submitChallengeAttempt(input),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.challenge }),
  });
}

export function useProposeProfile() {
  const api = useApi();
  return useMutation({ mutationFn: (input: ProfileRequest) => api.proposeProfile(input) });
}

export function useImportSuppliers() {
  const api = useApi();
  return useMutation({ mutationFn: (file: File) => api.importSuppliers(file) });
}

/**
 * The new company gets a blank workspace of its own (the visitor's demo keeps its invoices out of it); the browser
 * switches to it before the API sets it up, and back to the one it had if the API refuses the company.
 */
export function useCompleteOnboarding(store: WorkspaceStore = browserWorkspaceStore) {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({
    mutationFn: async (request: OnboardingRequest) => {
      const previous = { workspace_id: store.read(), api_key: store.readApiKey() };
      store.write(await api.createWorkspace("blank"));
      try {
        return await api.completeOnboarding(request);
      } catch (error) {
        const { workspace_id, api_key } = previous;
        if (workspace_id && api_key) store.write({ workspace_id, api_key });
        throw error;
      }
    },
    onSuccess: invalidate,
  });
}

export function useProcessInvoices() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({ mutationFn: () => api.processInvoices(), onSuccess: invalidate });
}

export function useReconciliations() {
  const api = useApi();
  return useQuery({ queryKey: queryKeys.reconciliations, queryFn: () => api.listReconciliations() });
}

export function useReconciliation(id: string | null) {
  const api = useApi();
  return useQuery({
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
  return useMutation({ mutationFn: (input: StatementInput) => api.reconcileStatement(input), onSuccess: store });
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
