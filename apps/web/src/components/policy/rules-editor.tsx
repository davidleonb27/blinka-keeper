"use client";

import { Check, Wand2 } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import type { Policy, PolicyProposal } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { useApplyPolicy, useCompilePolicy } from "@/lib/api/hooks";
import { submitOnEnter } from "@/lib/keyboard";
import { ProposalView } from "./proposal-view";
import { SimulationView } from "./simulation-view";

const EXAMPLES = [
  "Nada sobre 3.000 USD sin que lo apruebe Ana",
  "La reserva de nómina es de 70 mil",
  "Bloquea a Tango Data",
  "El cupo del agente es de 30 mil y la tolerancia de 5 %",
];

export function RulesEditor({ policy }: { policy: Policy }) {
  const textId = useId();
  const [text, setText] = useState("");
  const [proposal, setProposal] = useState<PolicyProposal | null>(null);
  const compile = useCompilePolicy();
  const apply = useApplyPolicy();

  const run = (value: string) => {
    if (!value.trim()) return;
    compile.mutate({ text: value }, { onSuccess: setProposal, onError: (e) => toast.error(messageOf(e)) });
  };

  const applyProposal = (next: PolicyProposal) =>
    apply.mutate(next.proposed, {
      onSuccess: () => {
        toast.success("Reglas aplicadas. El cambio quedó en el registro.");
        setProposal(null);
        setText("");
      },
      onError: (e) => toast.error(messageOf(e)),
    });

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="card-surface flex flex-col gap-3 p-5" aria-labelledby={`${textId}-title`}>
        <h2 id={`${textId}-title`} className="font-semibold">Escribe la regla como se la dirías a tu contador</h2>
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            run(text);
          }}
        >
          <label htmlFor={textId} className="sr-only">Regla en español</label>
          <textarea
            id={textId}
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={submitOnEnter}
            placeholder="Pide permiso para pagos de más de 3.000 dólares"
            className="w-full resize-none rounded-xl border border-line-2 bg-surface-2 px-3.5 py-3 text-[15px]"
          />
          <Button type="submit" className="self-start" disabled={compile.isPending || !text.trim()}>
            <Wand2 aria-hidden /> {compile.isPending ? "Compilando…" : "Compilar y simular"}
          </Button>
        </form>
        <div>
          <p className="mb-2 text-[12.5px] text-ink-3">Prueba con:</p>
          <ul className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((example) => (
              <li key={example}>
                <button
                  type="button"
                  onClick={() => {
                    setText(example);
                    run(example);
                  }}
                  className="rounded-full border border-dashed border-line-2 px-3 py-1.5 text-[12.5px] text-ink-2 hover:border-solid hover:text-ink"
                >
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </div>
        {proposal ? <ProposalView proposal={proposal} currency={policy.base_currency} /> : null}
      </section>
      <section className="card-surface flex flex-col gap-3 p-5 lg:sticky lg:top-6 lg:self-start" aria-label="Antes de aplicar">
        <h2 className="font-semibold">Antes de aplicar</h2>
        {proposal?.simulation ? (
          <>
            <SimulationView report={proposal.simulation} />
            <Button variant="approve" disabled={apply.isPending || !proposal.changes.length} onClick={() => applyProposal(proposal)}>
              <Check aria-hidden /> Aplicar estas reglas
            </Button>
          </>
        ) : (
          <p className="text-[13.5px] text-ink-3">
            Compila una regla y aquí verás qué facturas de este mes cambiarían de decisión. Nada se aplica sin tu clic.
          </p>
        )}
      </section>
    </div>
  );
}
