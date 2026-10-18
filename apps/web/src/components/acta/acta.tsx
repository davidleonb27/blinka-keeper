"use client";

import { Check, Link2, ShieldAlert, X } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { StatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";
import { sealOf, type Acta as ActaData } from "@/lib/api/client";
import type { ExtractedFieldName, Policy } from "@/lib/api/contracts";
import { formatDate, formatDateTime, shortHash } from "@/lib/format";
import { amountText, baseAmountText, supplierText } from "@/lib/presentation";
import { ExtractedFields } from "./extracted-fields";
import { OriginalDocument } from "./original-document";
import { PaymentExecutionBlock } from "./payment-execution";
import { PaymentProgress, type PaymentStep } from "./payment-progress";
import { UnknownSupplierHint } from "@/components/suppliers/unknown-supplier-hint";
import { RuleList } from "./rule-list";

export interface ActaProps {
  detail: ActaData;
  policy: Pick<Policy, "approvers" | "min_confidence" | "base_currency">;
  onDecide: (approve: boolean, approver: string) => void;
  deciding: boolean;
  onRetryPayment: () => void;
  retryingPayment: boolean;
  /** The approval just sent from this acta, while it travels to the rail and once the rail answered. */
  paymentStep?: PaymentStep | null;
  /** The signed receipt of this decision, shown next to the ledger seal. */
  receipt?: ReactNode;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="eyebrow mb-2.5">{title}</h3>
      {children}
    </section>
  );
}

function ActaHeader({ detail, baseCurrency }: { detail: ActaData; baseCurrency: string }) {
  const { decision, invoice } = detail;
  const base = baseAmountText(decision, baseCurrency);
  return (
    <header className="flex flex-col gap-2.5 pr-12">
      <p className="eyebrow">Acta de decisión · {decision.invoice_id}</p>
      <h2 className="font-serif text-2xl leading-tight font-semibold tracking-[-0.01em]">{supplierText(decision)}</h2>
      <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
        <b className="text-[26px] leading-none font-semibold tracking-[-0.02em] tabular">{amountText(decision)}</b>
        {base ? <span className="text-ink-3 tabular">{base}</span> : null}
        <span className="text-ink-3">llegó el {formatDate(invoice.received_at)}</span>
      </p>
      <div>
        <StatusPill status={decision.status} size="lg" />
      </div>
    </header>
  );
}

function ApprovalActions({ policy, onDecide, deciding }: Pick<ActaProps, "policy" | "onDecide" | "deciding">) {
  const selectId = useId();
  const names = policy.approvers.map((a) => a.name);
  const [approver, setApprover] = useState(names[0] ?? "");
  return (
    <div className="sticky bottom-0 -mx-5 mt-2 flex flex-wrap items-center gap-2.5 border-t border-line-2 bg-surface px-5 py-3.5 sm:-mx-6 sm:px-6">
      <label htmlFor={selectId} className="flex w-full items-center gap-2 text-[12.5px] text-ink-3 sm:mr-auto sm:w-auto">
        Decides como
        <select
          id={selectId}
          value={approver}
          onChange={(event) => setApprover(event.target.value)}
          className="h-10 rounded-[10px] border border-line-2 bg-surface-2 px-2.5 text-[13px] text-ink"
        >
          {names.map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </label>
      <Button variant="reject" className="flex-1 sm:flex-none" disabled={deciding || !approver} onClick={() => onDecide(false, approver)}>
        <X aria-hidden /> Rechazar
      </Button>
      <Button variant="approve" className="flex-1 sm:flex-none" disabled={deciding || !approver} onClick={() => onDecide(true, approver)}>
        <Check aria-hidden /> Aprobar pago
      </Button>
    </div>
  );
}

export function Acta({
  detail,
  policy,
  onDecide,
  deciding,
  onRetryPayment,
  retryingPayment,
  paymentStep = null,
  receipt,
}: ActaProps) {
  const [activeField, setActiveField] = useState<ExtractedFieldName | null>(null);
  const { decision, invoice } = detail;
  const { extraction } = invoice;
  const seal = sealOf(detail);
  const paid = decision.agent_verdict === "pay";
  return (
    <article className="flex flex-col gap-6">
      <ActaHeader detail={detail} baseCurrency={policy.base_currency} />

      <Section title="Por qué">
        <p className="max-w-[62ch] text-[15px] leading-relaxed">{decision.explanation}</p>
        {decision.narrative ? (
          <p className="mt-3 max-w-[62ch] rounded-xl bg-surface-2 px-3.5 py-3 text-[14px] text-ink-2">
            <span className="font-semibold text-ink">En palabras simples: </span>
            {decision.narrative}
          </p>
        ) : null}
        {decision.blocked_reason ? (
          <p className="mt-3 flex gap-2 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
            <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-crit" />
            Aprobada, pero no se paga: {decision.blocked_reason}
          </p>
        ) : null}
      </Section>

      <PaymentProgress step={paymentStep} />

      <PaymentExecutionBlock
        decision={decision}
        paidByItsAgent={extraction.source === "intent"}
        onRetry={onRetryPayment}
        retrying={retryingPayment}
      />

      {decision.counterfactual ? (
        <Section title={paid ? "Qué habría cambiado la decisión" : "Qué tendría que cambiar"}>
          <p className="max-w-[62ch] text-ink-2">{decision.counterfactual}</p>
        </Section>
      ) : null}

      <Section title="Reglas evaluadas">
        <UnknownSupplierHint decision={decision} />
        <RuleList rules={decision.rules} />
      </Section>

      <Section title="Lo que leyó del documento">
        <ExtractedFields extraction={extraction} minConfidence={policy.min_confidence} onFocusField={setActiveField} />
      </Section>
      <Section title="Documento original">
        <OriginalDocument extraction={extraction} activeField={activeField} />
      </Section>

      {decision.approval ? (
        <p className="text-[13px] text-ink-2">
          {decision.approval.decision === "approved" ? "Aprobada" : "Rechazada"} por{" "}
          <b className="text-ink">{decision.approval.approver}</b> · {formatDateTime(decision.approval.at)}
        </p>
      ) : null}

      {seal ? (
        <p className="flex flex-wrap items-center gap-x-3.5 gap-y-1.5 border-t border-line pt-3.5 text-xs text-ink-3">
          <Link2 aria-hidden className="size-3.5" />
          <span>Asiento #{seal.seq}</span>
          <span>
            hash <code className="font-mono text-ink-2">{shortHash(seal.hash)}</code>
          </span>
        </p>
      ) : null}
      {receipt}

      {decision.status === "pending_approval" ? (
        <ApprovalActions policy={policy} onDecide={onDecide} deciding={deciding} />
      ) : null}
    </article>
  );
}
