"use client";

import { Check, FileSignature, ShieldAlert, X } from "lucide-react";
import { useId, useRef, useState } from "react";
import { SimulationView } from "@/components/policy/simulation-view";
import { Button } from "@/components/ui/button";
import type { AgreementInput, AgreementPreview } from "@/lib/api/client";
import type { Agreement, Decision, PolicyChange } from "@/lib/api/contracts";

/** No approval skips these; the API checks them again when someone approves. */
const HARD_RULES = new Set(["R2", "R4", "R5", "R14"]);
const MIN_REASON = 3;
/** One-click reasons for the common cases; any of them can still be edited before approving. */
const QUICK_REASONS = ["Confirmado con el proveedor", "Monto verificado con la orden de compra", "Excepción aprobada por gerencia"];

export type HumanChoice =
  | { kind: "reject"; approver: string }
  | { kind: "once"; approver: string; reason: string }
  | { kind: "agreement"; approver: string; reason: string; agreement: AgreementInput; expectedVersion: number };

export interface ApprovalChoicesProps {
  decision: Decision;
  approvers: string[];
  agreement?: Agreement | null; // the supplier's agreement now, if it has one
  onDecide: (choice: HumanChoice) => void;
  onPreviewAgreement: (agreement: AgreementInput) => Promise<AgreementPreview>;
  deciding: boolean;
}

function failingHardRules(decision: Decision) {
  return decision.rules.filter((r) => HARD_RULES.has(r.rule_id) && (r.outcome === "hold" || r.outcome === "escalate"));
}

function shown(value: unknown): string {
  return value === null || value === undefined ? "sin valor" : String(value);
}

function ChangeList({ changes }: { changes: PolicyChange[] }) {
  return (
    <ul className="flex flex-col gap-1.5 text-[13.5px]">
      {changes.map((change) => (
        <li key={change.field}>
          {change.label}: <s className="text-ink-3">{shown(change.before)}</s> → <b>{shown(change.after)}</b>
        </li>
      ))}
    </ul>
  );
}

function numberOrNull(text: string): string | null {
  const trimmed = text.trim().replace(",", ".");
  return trimmed ? trimmed : null;
}

interface AgreementPanelProps {
  decision: Decision;
  agreement: Agreement | null;
  onPreview: (agreement: AgreementInput) => Promise<AgreementPreview>;
  preview: { input: AgreementInput; result: AgreementPreview } | null;
  setPreview: (preview: { input: AgreementInput; result: AgreementPreview } | null) => void;
}

function AgreementPanel({ decision, agreement, onPreview, preview, setPreview }: AgreementPanelProps) {
  const amountId = useId();
  const toleranceId = useId();
  // A monthly cap is not one invoice's amount: suggesting this invoice's would cut the month's cap to it.
  const monthlyCap = agreement?.kind === "monthly_cap";
  const [amount, setAmount] = useState(monthlyCap || decision.amount === null ? "" : String(decision.amount));
  const [tolerance, setTolerance] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input: AgreementInput = { amount: numberOrNull(amount), tolerance_pct: numberOrNull(tolerance) };
  const empty = input.amount === null && input.tolerance_pct === null;

  const edit = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setPreview(null); // a confirmation always matches the simulation the person saw
  };

  const simulate = async () => {
    setSimulating(true);
    setError(null);
    try {
      setPreview({ input, result: await onPreview(input) });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No pudimos simular el cambio.");
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line-2 bg-surface-2 px-3.5 py-3">
      <p className="text-[13.5px] text-ink-2">
        Cambia el acuerdo con {decision.supplier_name ?? "este proveedor"} desde ahora. Se guarda como una versión nueva
        de la política; las decisiones pasadas conservan la versión con la que se tomaron.
      </p>
      <div className="grid grid-cols-2 gap-2.5">
        <label htmlFor={amountId} className="flex flex-col gap-1 text-[12.5px] text-ink-3">
          {monthlyCap ? "Nuevo tope mensual" : "Nuevo monto acordado"} (
          {agreement?.currency ?? decision.currency ?? "moneda del acuerdo"})
          <input
            id={amountId}
            inputMode="decimal"
            value={amount}
            onChange={(event) => edit(setAmount)(event.target.value)}
            className="h-10 rounded-[10px] border border-line-2 bg-surface px-2.5 text-[13px] text-ink tabular"
          />
        </label>
        <label htmlFor={toleranceId} className="flex flex-col gap-1 text-[12.5px] text-ink-3">
          Tolerancia de este proveedor (%)
          <input
            id={toleranceId}
            inputMode="decimal"
            placeholder="la de la política"
            value={tolerance}
            onChange={(event) => edit(setTolerance)(event.target.value)}
            className="h-10 rounded-[10px] border border-line-2 bg-surface px-2.5 text-[13px] text-ink tabular"
          />
        </label>
      </div>
      <div>
        <Button variant="outline" disabled={empty || simulating} onClick={() => void simulate()}>
          {simulating ? "Simulando…" : "Simular el cambio"}
        </Button>
      </div>
      {error ? <p className="text-[13px] text-crit">{error}</p> : null}
      {preview ? (
        <div className="flex flex-col gap-3">
          <ChangeList changes={preview.result.changes} />
          <SimulationView report={preview.result.simulation} />
        </div>
      ) : null}
    </div>
  );
}

/**
 * The approval zone of a pending acta: reject, approve only this once (with a mandatory reason), or approve and update
 * the supplier's agreement after simulating it. A failing hard rule leaves only «Rechazar».
 */
export function ApprovalChoices({
  decision,
  approvers,
  agreement = null,
  onDecide,
  onPreviewAgreement,
  deciding,
}: ApprovalChoicesProps) {
  const selectId = useId();
  const reasonId = useId();
  const [approver, setApprover] = useState(approvers[0] ?? "");
  const [reason, setReason] = useState("");
  const [missingReason, setMissingReason] = useState(false);
  const reasonRef = useRef<HTMLInputElement>(null);
  const [updating, setUpdating] = useState(false);
  const [preview, setPreview] = useState<{ input: AgreementInput; result: AgreementPreview } | null>(null);
  const hard = failingHardRules(decision);
  const hasReason = reason.trim().length >= MIN_REASON;
  const canApprove = !deciding && Boolean(approver) && hard.length === 0;
  const canUpdate = decision.beneficiary_id !== null;

  const approveOnce = () => {
    if (!hasReason) {
      setMissingReason(true);
      reasonRef.current?.focus();
      return;
    }
    onDecide({ kind: "once", approver, reason: reason.trim() });
  };

  const chooseReason = (text: string) => {
    setReason(text);
    setMissingReason(false);
  };

  const approveWithAgreement = () => {
    if (!preview) return;
    onDecide({
      kind: "agreement",
      approver,
      reason: reason.trim(),
      agreement: preview.input,
      expectedVersion: preview.result.policy_version,
    });
  };

  return (
    <>
      <section aria-label="Aprobación" className="flex flex-col gap-3">
        <h3 className="eyebrow">Tu decisión</h3>
        {hard.length ? (
          <p role="note" className="flex gap-2 rounded-xl bg-crit-weak px-3.5 py-3 text-[14px]">
            <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-crit" />
            No se puede aprobar: {hard.map((r) => `${r.rule_id} ${r.label}`).join(", ")}. Estas reglas no se saltan con
            una aprobación; sólo puedes rechazarla.
          </p>
        ) : null}
        {updating && canApprove ? (
          <>
            <AgreementPanel decision={decision} agreement={agreement} onPreview={onPreviewAgreement} preview={preview} setPreview={setPreview} />
            <div>
              <Button variant="approve" disabled={!preview || !hasReason || deciding} onClick={approveWithAgreement}>
                <FileSignature aria-hidden /> Confirmar: aprobar y guardar la versión{" "}
                {preview ? preview.result.policy_version + 1 : "nueva"}
              </Button>
            </div>
          </>
        ) : null}
      </section>
      <div className="sticky bottom-0 -mx-5 mt-2 flex flex-wrap items-center gap-2.5 border-t border-line-2 bg-surface px-5 py-3.5 sm:-mx-6 sm:px-6">
        {hard.length ? null : (
          <div className="flex w-full flex-col gap-1.5">
            <label htmlFor={reasonId} className="text-[12.5px] text-ink-3">
              Motivo para aprobar (obligatorio; queda en el registro)
            </label>
            <input
              id={reasonId}
              ref={reasonRef}
              value={reason}
              maxLength={500}
              onChange={(event) => chooseReason(event.target.value)}
              placeholder="Por ejemplo: el proveedor subió el precio y lo confirmé por teléfono."
              aria-invalid={missingReason && !hasReason}
              className="h-10 w-full rounded-[10px] border border-line-2 bg-surface-2 px-2.5 text-[13.5px] text-ink aria-[invalid=true]:border-crit"
            />
            <div className="flex flex-wrap gap-1.5">
              {QUICK_REASONS.map((text) => (
                <button
                  key={text}
                  type="button"
                  onClick={() => chooseReason(text)}
                  className="rounded-full border border-line-2 px-2.5 py-1 text-[12px] text-ink-2 hover:bg-surface-2"
                >
                  {text}
                </button>
              ))}
            </div>
            {missingReason && !hasReason ? (
              <p role="alert" className="text-[12.5px] text-crit">
                Escribe o elige un motivo para aprobar.
              </p>
            ) : null}
          </div>
        )}
        <label htmlFor={selectId} className="flex w-full items-center gap-2 text-[12.5px] text-ink-3 sm:mr-auto sm:w-auto">
          Decides como
          <select
            id={selectId}
            value={approver}
            onChange={(event) => setApprover(event.target.value)}
            className="h-10 rounded-[10px] border border-line-2 bg-surface-2 px-2.5 text-[13px] text-ink"
          >
            {approvers.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <Button variant="reject" className="flex-1 sm:flex-none" disabled={deciding || !approver} onClick={() => onDecide({ kind: "reject", approver })}>
          <X aria-hidden /> Rechazar
        </Button>
        <Button
          variant="approve"
          className="flex-1 sm:flex-none"
          disabled={!canApprove}
          onClick={approveOnce}
        >
          <Check aria-hidden /> Aprobar sólo esta vez
        </Button>
        {canUpdate ? (
          <Button variant="outline" className="flex-1 sm:flex-none" disabled={!canApprove} aria-expanded={updating} onClick={() => setUpdating((open) => !open)}>
            <FileSignature aria-hidden /> Aprobar y actualizar el acuerdo
          </Button>
        ) : null}
      </div>
    </>
  );
}
