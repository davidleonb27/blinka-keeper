"use client";

import { EyeOff, Play, ShieldCheck, Square, Swords } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useReducer, useRef, useState } from "react";
import { PageHeader } from "@/components/shell/page-header";
import { StatusPill } from "@/components/status-pill";
import { Button } from "@/components/ui/button";
import { useApi } from "@/components/providers/api-provider";
import type { RedTeamEvent } from "@/lib/api/contracts";
import { messageOf } from "@/lib/api/errors";
import { failingRules } from "@/lib/presentation";
import { cn } from "@/lib/utils";
import { applyEvent, INITIAL_ARENA, type ArenaRound, type ArenaState } from "./arena-state";

const ROUND_OPTIONS = [3, 5];

type ArenaAction = { kind: "reset" } | { kind: "event"; event: RedTeamEvent };

function arenaReducer(state: ArenaState, action: ArenaAction): ArenaState {
  return action.kind === "reset" ? INITIAL_ARENA : applyEvent(state, action.event);
}

function Score({ label, value, tone }: { label: string; value: number; tone?: "good" | "bad" }) {
  return (
    <div className="rounded-xl border border-line px-3 py-2.5">
      <span className="block text-xs text-ink-3">{label}</span>
      <b className={cn("text-[26px] font-semibold tabular", tone === "good" && "text-pay", tone === "bad" && "text-crit")}>{value}</b>
    </div>
  );
}

function RoundCard({ round }: { round: ArenaRound }) {
  const { attack, decision } = round;
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <article className="card-surface flex flex-col gap-2.5 p-4">
        <p className="eyebrow text-crit">Atacante · ronda {round.round}</p>
        {attack ? (
          <>
            <h3 className="headline text-lg">{attack.technique}</h3>
            <p className="text-[13.5px] text-ink-2">{attack.rationale}</p>
            <pre className="overflow-x-auto rounded-xl border border-line bg-surface-2 px-3 py-2.5 font-mono text-[12px] leading-relaxed whitespace-pre-wrap">
              {attack.invoice_text}
            </pre>
            {attack.hidden_text ? (
              <p className="flex gap-2 rounded-xl border border-dashed border-crit bg-crit-weak px-3 py-2 font-mono text-[12px]">
                <EyeOff aria-hidden className="mt-0.5 size-3.5 shrink-0 text-crit" />
                <span>
                  <span className="sr-only">Texto oculto: </span>«{attack.hidden_text}»
                </span>
              </p>
            ) : null}
            <p className="text-xs text-ink-3">Apunta a {attack.target_rules.join(", ")} · se entrega como {attack.render_as}</p>
          </>
        ) : (
          <p className="animate-pulse text-[13.5px] text-ink-3">Pensando el próximo ataque…</p>
        )}
      </article>
      <article className="card-surface flex flex-col gap-2.5 p-4">
        <p className="eyebrow text-brand">Defensor · reglas en código</p>
        {decision ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill status={decision.status} size="lg" />
              {round.caught ? (
                <span className="inline-flex items-center gap-1 text-[13px] font-semibold text-pay">
                  <ShieldCheck aria-hidden className="size-4" /> Atrapado
                </span>
              ) : null}
            </div>
            <ul className="flex flex-wrap gap-1.5">
              {failingRules(decision).map((rule) => (
                <li
                  key={rule.rule_id}
                  className={cn(
                    "rounded-full px-2.5 py-1 text-xs font-semibold",
                    rule.outcome === "hold" ? "bg-hold-weak text-hold" : "bg-esc-weak text-esc",
                  )}
                >
                  {rule.rule_id} · {rule.label}
                </li>
              ))}
            </ul>
            <p className="text-[13.5px] text-ink-2">{decision.explanation}</p>
          </>
        ) : (
          <p className="text-[13.5px] text-ink-3">{attack ? "Leyendo y decidiendo…" : "Esperando la factura."}</p>
        )}
      </article>
    </div>
  );
}

export function Arena() {
  const api = useApi();
  const reduceMotion = useReducedMotion();
  const [state, dispatch] = useReducer(arenaReducer, INITIAL_ARENA);
  const [rounds, setRounds] = useState(ROUND_OPTIONS[0]);
  const [running, setRunning] = useState(false);
  const abort = useRef<AbortController | null>(null);

  const start = async () => {
    dispatch({ kind: "reset" });
    setRunning(true);
    const controller = new AbortController();
    abort.current = controller;
    try {
      await api.runRedTeam({ rounds }, (event) => dispatch({ kind: "event", event }), controller.signal);
    } catch (error) {
      if (!controller.signal.aborted) dispatch({ kind: "event", event: { type: "error", round: 0, message: messageOf(error) } });
    } finally {
      setRunning(false);
    }
  };

  const stop = () => {
    abort.current?.abort();
    setRunning(false);
  };

  return (
    <>
      <PageHeader
        title="Arena: ataque contra defensa"
        subtitle="Un atacante genera facturas fraudulentas contra tus reglas, lee por qué lo bloquearon y cambia de técnica. El defensor no cambia: las reglas son código."
      >
        <Button asChild variant="outline">
          <Link href="/reto">Intenta engañarlo tú</Link>
        </Button>
      </PageHeader>
      <section className="card-surface mb-4 flex flex-col gap-4 p-5" aria-label="Marcador">
        <div className="flex flex-wrap items-center gap-3">
          <div role="group" aria-label="Rondas" className="flex gap-1.5">
            {ROUND_OPTIONS.map((n) => (
              <button
                key={n}
                type="button"
                aria-pressed={rounds === n}
                disabled={running}
                onClick={() => setRounds(n)}
                className={cn(
                  "h-10 rounded-full border border-line-2 px-4 text-[13px] font-medium text-ink-2",
                  rounds === n && "border-ink bg-ink text-background",
                )}
              >
                {n} rondas
              </button>
            ))}
          </div>
          {running ? (
            <Button variant="outline" onClick={stop}>
              <Square aria-hidden /> Detener
            </Button>
          ) : (
            <Button onClick={() => void start()}>
              <Play aria-hidden /> {state.rounds.length ? "Otra vez" : "Empezar el ataque"}
            </Button>
          )}
        </div>
        <div className="grid grid-cols-3 gap-2" aria-live="polite">
          <Score label="Ataques" value={state.score.attacks} />
          <Score label="Atrapados" value={state.score.caught} tone="good" />
          <Score label="Pagos indebidos" value={state.score.improper} tone={state.score.improper ? "bad" : "good"} />
        </div>
        {state.summary ? <p className="font-semibold text-pay">{state.summary}</p> : null}
        {state.error ? <p role="alert" className="text-crit">{state.error}</p> : null}
      </section>
      {state.rounds.length ? (
        <ol className="flex flex-col gap-4">
          <AnimatePresence initial={false}>
            {state.rounds.toReversed().map((round) => (
              <motion.li
                key={round.round}
                initial={reduceMotion ? false : { opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <RoundCard round={round} />
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      ) : (
        <div className="card-surface flex flex-col items-center gap-3 px-6 py-14 text-center">
          <Swords aria-hidden className="size-9 text-brand" />
          <p className="max-w-[46ch] text-ink-2">
            Cada ataque se lee, se decide con las mismas quince reglas y queda en el{" "}
            <Link href="/registro" className="font-semibold text-brand underline-offset-4 hover:underline">registro</Link>.
          </p>
        </div>
      )}
    </>
  );
}
