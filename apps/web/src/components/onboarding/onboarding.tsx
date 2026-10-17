"use client";

import { X } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useCallback, useState, type ReactNode } from "react";
import { Wordmark } from "@/components/brand/seal";
import { ModeBadge } from "@/components/shell/mode-badge";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { messageOf } from "@/lib/api/errors";
import { useProposeProfile } from "@/lib/api/hooks";
import { ApproversStep, CompanyStep, MoneyStep, ProfileStep, type StepProps } from "./basic-steps";
import { ReadyStep, SimulationStep } from "./finish-steps";
import { RulesStep } from "./rules-step";
import { SuppliersStep } from "./suppliers-step";
import {
  fallbackProfile,
  INITIAL_ANSWERS,
  normalizeWebsite,
  STEPS,
  validateStep,
  withProfile,
  type Answers,
  type StepId,
} from "./state";

const SLIDE_PX = 28;

const STEP_VIEWS: Record<Exclude<StepId, "ready">, (props: StepProps) => ReactNode> = {
  company: CompanyStep,
  profile: ProfileStep,
  money: MoneyStep,
  approvers: ApproversStep,
  rules: RulesStep,
  suppliers: SuppliersStep,
  simulation: SimulationStep,
};

function Progress({ index }: { index: number }) {
  const value = index + 1;
  return (
    <div
      role="progressbar"
      aria-label="Progreso de la configuración"
      aria-valuemin={1}
      aria-valuemax={STEPS.length}
      aria-valuenow={value}
      aria-valuetext={`Paso ${value} de ${STEPS.length}`}
      className="h-1 w-full overflow-hidden bg-line"
    >
      <i className="block h-full bg-brand transition-[width] duration-500 ease-out" style={{ width: `${(value / STEPS.length) * 100}%` }} />
    </div>
  );
}

/** One question per screen. Every answer is validated before Enter moves on; nothing is lost going back. */
export function Onboarding() {
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const [answers, setAnswers] = useState<Answers>(INITIAL_ANSWERS);
  const [error, setError] = useState<string | null>(null);
  const [profileFailed, setProfileFailed] = useState(false);
  const reduceMotion = useReducedMotion();
  const propose = useProposeProfile();
  const step = STEPS[index];

  const update = useCallback((patch: Partial<Answers>) => {
    setAnswers((current) => ({ ...current, ...patch }));
    setError(null);
  }, []);

  const go = (delta: number) => {
    setDirection(delta);
    setIndex((current) => Math.min(STEPS.length - 1, Math.max(0, current + delta)));
    setError(null);
  };

  const proposeProfile = () =>
    propose.mutate(
      { company_name: answers.companyName.trim(), website: normalizeWebsite(answers.website) },
      {
        onSuccess: (profile) => {
          setAnswers((current) => withProfile(current, profile));
          go(1);
        },
        onError: (failure) => {
          setProfileFailed(true);
          setError(messageOf(failure));
        },
      },
    );

  const continueWithoutProfile = () => {
    setAnswers((current) => withProfile(current, fallbackProfile(current)));
    setProfileFailed(false);
    go(1);
  };

  const submit = () => {
    const problem = validateStep(step, answers);
    if (problem) return setError(problem);
    if (step === "company") return proposeProfile();
    go(1);
  };

  const frame = {
    number: index + 1,
    error,
    onSubmit: submit,
    onBack: index > 0 ? () => go(-1) : undefined,
    busy: step === "company" && propose.isPending,
  };

  const View = step === "ready" ? null : STEP_VIEWS[step];
  const offset = reduceMotion ? 0 : SLIDE_PX * direction;

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-10 bg-background/90 pt-[env(safe-area-inset-top)] backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-3 px-4">
          <Link href="/" aria-label="Custodio, inicio" className="rounded-lg">
            <Wordmark />
          </Link>
          <div className="flex items-center gap-1">
            <span className="mr-2 hidden text-[13px] text-ink-3 tabular sm:inline">
              {index + 1} de {STEPS.length}
            </span>
            <ModeBadge />
            <ThemeToggle />
            <Link
              href="/"
              aria-label="Salir de la configuración"
              className="grid size-10 place-items-center rounded-[10px] text-ink-2 hover:bg-surface-2"
            >
              <X aria-hidden className="size-5" />
            </Link>
          </div>
        </div>
        <Progress index={index} />
      </header>
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-4 py-10 sm:py-16">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={{ opacity: 0, y: offset }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -offset }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            {View ? <View answers={answers} update={update} frame={frame} /> : <ReadyStep answers={answers} />}
            {step === "company" && profileFailed ? (
              <button type="button" onClick={continueWithoutProfile} className="mt-4 text-[14px] font-semibold text-brand underline-offset-4 hover:underline">
                Seguir sin perfil propuesto
              </button>
            ) : null}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
