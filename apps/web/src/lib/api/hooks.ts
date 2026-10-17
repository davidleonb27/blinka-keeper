"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApi } from "@/components/providers/api-provider";
import type { ApprovalInput, ChallengeInput, OnboardingRequest, ProfileRequest } from "./client";
import type { Policy } from "./contracts";

const CHALLENGE_POLL_MS = 5_000;

const queryKeys = {
  workspace: ["workspace"] as const,
  decisions: ["decisions"] as const,
  decision: (id: string) => ["decisions", id] as const,
  policy: ["policy"] as const,
  ledger: ["ledger"] as const,
  challenge: ["challenge-stats"] as const,
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

export function useCompleteOnboarding() {
  const api = useApi();
  const invalidate = useInvalidateWorkspace();
  return useMutation({
    mutationFn: (request: OnboardingRequest) => api.completeOnboarding(request),
    onSuccess: invalidate,
  });
}
