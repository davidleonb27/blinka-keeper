"use client";

import { useEffect, useId } from "react";
import { ProposalView } from "@/components/policy/proposal-view";
import { messageOf } from "@/lib/api/errors";
import { useCompilePolicy } from "@/lib/api/hooks";
import { submitOnEnter } from "@/lib/keyboard";
import type { StepProps } from "./basic-steps";
import { StepFrame } from "./step-frame";
import { compileKey, type CompileInput } from "./state";

const COMPILE_DEBOUNCE_MS = 600;

export function RulesStep({ answers, update, frame }: StepProps) {
  const textId = useId();
  const compile = useCompilePolicy();
  const { mutate } = compile;
  // A string key, so storing the proposal (a new `answers`) does not trigger another compile.
  const key = compileKey(answers);

  useEffect(() => {
    const input = JSON.parse(key) as CompileInput;
    if (!input.text) return;
    const timer = setTimeout(
      () => mutate(input, { onSuccess: (proposal) => update({ proposal, proposalKey: key }) }),
      COMPILE_DEBOUNCE_MS,
    );
    return () => clearTimeout(timer);
  }, [key, mutate, update]);

  return (
    <StepFrame
      {...frame}
      busy={compile.isPending}
      busyLabel="Compilando tus reglas…"
      title="Tus reglas, en tus palabras"
      helper="Escríbelas como se las dirías a tu contador. Blinka Keeper las compila en vivo; lo que no entienda, te lo pregunta en vez de adivinar."
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor={textId} className="text-[14px] font-medium text-ink-2">
          Reglas
        </label>
        <textarea
          id={textId}
          autoFocus
          rows={4}
          value={answers.rulesText}
          onKeyDown={submitOnEnter}
          onChange={(e) => update({ rulesText: e.target.value, proposal: null })}
          placeholder="Nada sobre 3.000 USD sin que lo apruebe Ana."
          className="w-full resize-none rounded-xl border border-line-2 bg-surface px-4 py-3.5 text-lg leading-relaxed focus-visible:border-brand"
        />
        <p className="text-[13px] text-ink-3">Shift + Enter para una línea nueva.</p>
      </div>
      {compile.error ? <p className="text-[13.5px] text-crit">{messageOf(compile.error)}</p> : null}
      {answers.proposal ? <ProposalView proposal={answers.proposal} currency={answers.currency} /> : null}
    </StepFrame>
  );
}
