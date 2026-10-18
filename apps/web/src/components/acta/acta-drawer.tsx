"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";
import { CorrectionPanel } from "@/components/corrections/correction-panel";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import type { Decision } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import {
  useAgreementPreview,
  useApproveOnce,
  useApproveWithAgreement,
  useDecision,
  useHealth,
  useHumanDecision,
  usePolicy,
  useRetryPayment,
} from "@/lib/api/hooks";
import { STATUS_META } from "@/lib/presentation";
import { markTourStep } from "@/lib/tour";
import { Acta } from "./acta";
import type { HumanChoice } from "./approval-choices";
import type { PaymentStep } from "./payment-progress";
import { SignedReceipt } from "./signed-receipt";

const ACTA_PARAM = "acta";

function ActaContent({ invoiceId }: { invoiceId: string }) {
  const detail = useDecision(invoiceId);
  const policy = usePolicy();
  const decide = useHumanDecision(invoiceId);
  const once = useApproveOnce(invoiceId);
  const preview = useAgreementPreview(invoiceId);
  const withAgreement = useApproveWithAgreement(invoiceId);
  const retry = useRetryPayment(invoiceId);
  const rail = useHealth().data?.payment_rail ?? null;
  const opened = detail.data !== undefined;
  useEffect(() => {
    if (opened) markTourStep("acta");
  }, [opened]);

  if (detail.error || policy.error) {
    return <ErrorState error={detail.error ?? policy.error} onRetry={() => void detail.refetch()} />;
  }
  if (!detail.data || !policy.data) return <LoadingBlock label="Cargando el acta…" />;

  const settled = {
    onSuccess: (decision: Decision) => toast.success(`${invoiceId}: ${STATUS_META[decision.status].label.toLowerCase()}.`),
    onError: (error: Error) => toast.error(messageOf(error)),
  };
  const onDecide = (choice: HumanChoice) => {
    if (choice.kind === "reject") decide.mutate({ approve: false, input: { approver: choice.approver } }, settled);
    if (choice.kind === "once") once.mutate({ approver: choice.approver, reason: choice.reason }, settled);
    if (choice.kind === "agreement") {
      withAgreement.mutate(
        { ...choice.agreement, approver: choice.approver, reason: choice.reason, expected_policy_version: choice.expectedVersion },
        {
          onSuccess: (result) => {
            settled.onSuccess(result.decision);
            toast.success(`Acuerdo actualizado: la política pasó a la versión ${result.policy_version}.`);
          },
          onError: settled.onError,
        },
      );
    }
  };

  const onRetryPayment = () =>
    retry.mutate(undefined, {
      onSuccess: (decision) =>
        decision.execution?.status === "failed"
          ? toast.error(decision.execution.error ?? `${invoiceId}: el pago no salió.`)
          : toast.success(`${invoiceId}: pago ejecutado.`),
      onError: (error) => toast.error(messageOf(error)),
    });

  const approving = decide.variables?.approve === true;
  let paymentStep: PaymentStep | null = null;
  if (approving && decide.isPending) paymentStep = { phase: "sending", rail };
  else if (approving && decide.data) paymentStep = { phase: "done", decision: decide.data };

  return (
    <Acta
      detail={detail.data}
      paymentStep={paymentStep}
      policy={policy.data}
      onDecide={onDecide}
      onPreviewAgreement={(agreement) => preview.mutateAsync(agreement)}
      deciding={decide.isPending || once.isPending || withAgreement.isPending}
      onRetryPayment={onRetryPayment}
      retryingPayment={retry.isPending}
      receipt={<SignedReceipt invoiceId={invoiceId} />}
      correction={
        <CorrectionPanel invoiceId={invoiceId} cameByWhatsApp={detail.data.invoice.extraction.source === "whatsapp"} />
      }
    />
  );
}

/** The acta opens from ?acta=<invoice id>, so a shared link lands on it directly. */
export function ActaDrawer() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const invoiceId = params.get(ACTA_PARAM);

  const close = () => router.replace(pathname, { scroll: false });

  return (
    <Sheet open={invoiceId !== null} onOpenChange={(open) => (open ? undefined : close())}>
      <SheetContent side="right" className="gap-0 overflow-y-auto data-[side=right]:w-full border-line-2 bg-surface px-5 pt-5 pb-0 data-[side=right]:sm:max-w-[640px] sm:px-6">
        <SheetTitle className="sr-only">Acta de decisión {invoiceId}</SheetTitle>
        <SheetDescription className="sr-only">
          Las quince reglas, el documento leído y la decisión de Custodio para esta factura.
        </SheetDescription>
        {invoiceId ? (
          <div className="pb-6">
            <ActaContent invoiceId={invoiceId} />
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
