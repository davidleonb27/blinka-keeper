"use client";

import { ArrowRight, Lightbulb } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { Suggestion } from "@/lib/api/client";
import type { Policy } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useAcceptSuggestion, useSuggestions } from "@/lib/api/hooks";
import { formatDate, formatMoney, formatNumber } from "@/lib/format";
import { SimulationView } from "./simulation-view";

function percent(value: number): string {
  return `${formatNumber(value, 1)} %`;
}

function SuggestionCard({ suggestion, approvers }: { suggestion: Suggestion; approvers: string[] }) {
  const selectId = useId();
  const [approver, setApprover] = useState(approvers[0] ?? "");
  const [showSimulation, setShowSimulation] = useState(false);
  const accept = useAcceptSuggestion();

  const onAccept = () =>
    accept.mutate(
      { id: suggestion.id, input: { approver, expected_policy_version: suggestion.policy_version } },
      {
        onSuccess: (policy) => toast.success(`Aplicado: la política pasó a la versión ${policy.version}.`),
        onError: (error) => toast.error(messageOf(error)),
      },
    );

  return (
    <li className="card-surface flex flex-col gap-3 p-4">
      <p className="text-[15px] leading-relaxed font-semibold">{suggestion.question}</p>
      <p className="flex flex-wrap items-center gap-2 text-[14px] tabular">
        Tolerancia de {suggestion.supplier_name}:
        <span className="text-ink-3 line-through">{percent(suggestion.current_tolerance_pct)}</span>
        <ArrowRight aria-label="pasa a" className="size-3.5 text-ink-3" />
        <b className="text-brand">{percent(suggestion.proposed_tolerance_pct)}</b>
        <span className="text-[12.5px] text-ink-3">sólo este proveedor; los topes globales no cambian</span>
      </p>
      <div>
        <h3 className="eyebrow mb-1.5">La evidencia</h3>
        <ul className="flex flex-col gap-1.5 text-[13.5px]">
          {suggestion.evidence.map((item) => (
            <li key={item.invoice_id} className="rounded-xl border border-line px-3 py-2">
              <span className="tabular">
                {formatDate(item.approved_at)} · {formatMoney(item.amount, item.currency)} ({item.deviation_pct > 0 ? "+" : ""}
                {percent(item.deviation_pct)} del acuerdo)
              </span>{" "}
              · aprobada por <b>{item.approver}</b>
              {item.note ? <span className="text-ink-3"> · «{item.note}»</span> : null}
              {item.invoice_id.startsWith("INV-") ? (
                <>
                  {" "}
                  · <Link href={`/panel?acta=${item.invoice_id}`} className="underline">ver acta</Link>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
      <div>
        <Button variant="ghost" size="sm" aria-expanded={showSimulation} onClick={() => setShowSimulation((open) => !open)}>
          {showSimulation ? "Ocultar la simulación" : "Ver qué facturas cambiarían"}
        </Button>
        {showSimulation ? (
          <div className="mt-2">
            <SimulationView report={suggestion.simulation} />
          </div>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-2.5 border-t border-line pt-3">
        <label htmlFor={selectId} className="flex items-center gap-2 text-[12.5px] text-ink-3">
          Decides como
          <select
            id={selectId}
            value={approver}
            onChange={(event) => setApprover(event.target.value)}
            className="h-9 rounded-[10px] border border-line-2 bg-surface-2 px-2.5 text-[13px] text-ink"
          >
            {approvers.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>
        <Button variant="approve" disabled={!approver || accept.isPending} onClick={onAccept}>
          Sí, aplicar como versión {suggestion.policy_version + 1}
        </Button>
        <span className="text-[12.5px] text-ink-3">Nada cambia hasta que lo aceptes.</span>
      </div>
    </li>
  );
}

/** «Custodio sugiere»: agreement changes drawn from the exceptions people keep approving. Never applied on their own. */
export function SuggestionsPanel({ policy }: { policy: Pick<Policy, "approvers"> }) {
  const suggestions = useSuggestions();
  if (!suggestions.data?.length) return null;
  return (
    <section aria-label="Custodio sugiere" className="flex flex-col gap-3">
      <h2 className="flex items-center gap-2 text-[15px] font-semibold">
        <Lightbulb aria-hidden className="size-4 text-brand" /> Custodio sugiere
      </h2>
      <p className="max-w-[70ch] text-[13.5px] text-ink-2">
        Cuando apruebas varias veces la misma excepción, Custodio propone el ajuste del acuerdo que la evitaría, con su
        evidencia y su simulación. Nunca propone relajar las reglas duras ni los topes globales, y nada se aplica solo.
      </p>
      <ul className="flex flex-col gap-3">
        {suggestions.data.map((suggestion) => (
          <SuggestionCard key={suggestion.id} suggestion={suggestion} approvers={policy.approvers.map((a) => a.name)} />
        ))}
      </ul>
    </section>
  );
}
