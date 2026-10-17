"use client";

import { Check, Link2, ShieldAlert, X } from "lucide-react";
import { useId, useState, type ReactNode } from "react";
import { StatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";
import type { DecisionDetail } from "@/lib/api/client";
import type { ExtractedFieldName, Policy } from "@/lib/api/contracts";
import { formatDate, formatDateTime, shortHash } from "@/lib/format";
import { amountText, baseAmountText, supplierText } from "@/lib/presentation";
import { ExtractedFields } from "./extracted-fields";
import { OriginalDocument } from "./original-document";
import { RuleList } from "./rule-list";

export interface ActaProps {
  detail: DecisionDetail;
  policy: Pick<Policy, "approvers" | "min_confidence" | "base_currency">;
  onDecide: (approve: boolean, approver: string) => void;
  deciding: boolean;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="eyebrow mb-2.5">{title}</h3>
      {children}
    </section>
  );
}

function ActaHeader({ detail, baseCurrency }: { detail: DecisionDetail; baseCurrency: string }) {
  const { decision } = detail;
  const base = baseAmountText(decision, baseCurrency);
  const eyebrow = ["Acta de decisión", decision.invoice_id, detail.trap && `trampa: ${detail.trap.toLowerCase()}`]
    .filter(Boolean)
    .join(" · ");
  return (
    <header className="flex flex-col gap-2.5 pr-12">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="font-display text-2xl leading-tight font-semibold tracking-[-0.01em]">{supplierText(decision)}</h2>
      <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
        <b className="text-[26px] leading-none font-semibold tracking-[-0.02em] tabular">{amountText(decision)}</b>
        {base ? <span className="text-ink-3 tabular">{base}</span> : null}
        <span className="text-ink-3">llegó el {formatDate(detail.received_at)}</span>
      </p>
      <div>
        <StatusPill status={decision.status} size="lg" />
      </div>
    </header>
  );
}

function ApprovalActions({ policy, onDecide, deciding }: Omit<ActaProps, "detail">) {
  const selectId = useId();
  const names = policy.approvers.map((a) => a.name);
  const [approver, setApprover] = useState(names[0] ?? "");
  return (
    <div className="sticky bottom-0 -mx-5 mt-2 flex flex-wrap items-center gap-2.5 border-t border-line-2 bg-surface px-5 py-3.5 sm:-mx-6 sm:px-6">
      <label htmlFor={selectId} className="mr-auto flex items-center gap-2 text-[12.5px] text-ink-3">
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
      <Button variant="reject" disabled={deciding || !approver} onClick={() => onDecide(false, approver)}>
        <X aria-hidden /> Rechazar
      </Button>
      <Button variant="approve" disabled={deciding || !approver} onClick={() => onDecide(true, approver)}>
        <Check aria-hidden /> Aprobar pago
      </Button>
    </div>
  );
}

export function Acta({ detail, policy, onDecide, deciding }: ActaProps) {
  const [activeField, setActiveField] = useState<ExtractedFieldName | null>(null);
  const { decision, extraction, ledger } = detail;
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

      {decision.counterfactual ? (
        <Section title={paid ? "Qué habría cambiado la decisión" : "Qué tendría que cambiar"}>
          <p className="max-w-[62ch] text-ink-2">{decision.counterfactual}</p>
        </Section>
      ) : null}

      <Section title="Reglas evaluadas">
        <RuleList rules={decision.rules} />
      </Section>

      {extraction ? (
        <>
          <Section title="Lo que leyó del documento">
            <ExtractedFields extraction={extraction} minConfidence={policy.min_confidence} onFocusField={setActiveField} />
          </Section>
          <Section title="Documento original">
            <OriginalDocument extraction={extraction} activeField={activeField} />
          </Section>
        </>
      ) : null}

      {decision.approval ? (
        <p className="text-[13px] text-ink-2">
          {decision.approval.decision === "approved" ? "Aprobada" : "Rechazada"} por{" "}
          <b className="text-ink">{decision.approval.approver}</b> · {formatDateTime(decision.approval.at)}
        </p>
      ) : null}

      {ledger ? (
        <p className="flex flex-wrap items-center gap-x-3.5 gap-y-1.5 border-t border-line pt-3.5 text-xs text-ink-3">
          <Link2 aria-hidden className="size-3.5" />
          <span>Asiento #{ledger.seq}</span>
          <span>
            hash <code className="font-mono text-ink-2">{shortHash(ledger.hash)}</code>
          </span>
        </p>
      ) : null}

      {decision.status === "pending_approval" ? (
        <ApprovalActions policy={policy} onDecide={onDecide} deciding={deciding} />
      ) : null}
    </article>
  );
}
