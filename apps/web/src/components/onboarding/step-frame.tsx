"use client";

import { ArrowLeft, ArrowRight, CornerDownLeft, Loader2 } from "lucide-react";
import { useEffect, useId, useRef, type FormEvent, type InputHTMLAttributes, type KeyboardEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface StepFrameProps {
  number: number;
  title: string;
  helper?: ReactNode;
  children?: ReactNode;
  error: string | null;
  busy?: boolean;
  busyLabel?: string;
  nextLabel?: string;
  onSubmit: () => void;
  onBack?: () => void;
  aside?: ReactNode;
}

const HEADING_SELECTOR = "[data-step-heading]";
const OWN_ENTER = new Set(["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"]);

/** Puts focus back on the question, so the next Enter advances instead of repeating an action. */
export function focusStepHeading() {
  document.querySelector<HTMLElement>(HEADING_SELECTOR)?.focus();
}

/** Enter on the question itself (no field focused) advances too. Fields handle their own Enter. */
function advanceOnEnter(event: KeyboardEvent<HTMLFormElement>) {
  const target = event.target as HTMLElement;
  if (event.key !== "Enter" || OWN_ENTER.has(target.tagName)) return;
  event.preventDefault();
  event.currentTarget.requestSubmit();
}

export function StepFrame({
  number,
  title,
  helper,
  children,
  error,
  busy = false,
  busyLabel = "Un momento…",
  nextLabel = "Continuar",
  onSubmit,
  onBack,
  aside,
}: StepFrameProps) {
  const formRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    if (!formRef.current?.contains(document.activeElement)) focusStepHeading();
  }, []);
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!busy) onSubmit();
  };
  return (
    <form ref={formRef} onSubmit={handleSubmit} onKeyDown={advanceOnEnter} noValidate className="flex flex-col gap-7">
      <div>
        <p className="mb-3 flex items-center gap-2 font-mono text-[13px] text-brand">
          <span className="tabular">{String(number).padStart(2, "0")}</span>
          <ArrowRight aria-hidden className="size-3.5" />
        </p>
        <h1 data-step-heading tabIndex={-1} className="headline text-[30px] outline-none leading-[1.08] sm:text-[40px]">{title}</h1>
        {helper ? <div className="mt-3 max-w-[56ch] text-[15px] text-ink-2 sm:text-base">{helper}</div> : null}
      </div>
      {children}
      {error ? (
        <p role="alert" className="rounded-xl bg-crit-weak px-3.5 py-2.5 text-[14px] font-medium text-crit">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? <Loader2 aria-hidden className="animate-spin" /> : null}
          {busy ? busyLabel : nextLabel}
        </Button>
        <span className="hidden items-center gap-1.5 text-[13px] text-ink-3 sm:inline-flex">
          o pulsa <kbd className="inline-flex items-center gap-1 rounded-md border border-line-2 bg-surface px-1.5 py-0.5 font-mono text-xs">Enter <CornerDownLeft aria-hidden className="size-3" /></kbd>
        </span>
        {onBack ? (
          <Button type="button" variant="ghost" className="ml-auto" onClick={onBack}>
            <ArrowLeft aria-hidden /> Volver
          </Button>
        ) : null}
      </div>
      {aside}
    </form>
  );
}

interface BigFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

/** A Typeform-style field: a large underlined input with its label above. */
export function BigField({ label, hint, className, ...input }: BigFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[14px] font-medium text-ink-2">
        {label}
      </label>
      <input
        id={id}
        aria-describedby={hint ? hintId : undefined}
        className={cn(
          "h-14 w-full min-w-0 rounded-none border-0 border-b-2 border-line-2 bg-transparent px-0 text-xl font-medium text-ink placeholder:text-ink-3/70 focus-visible:border-brand focus-visible:outline-none sm:text-2xl",
          className,
        )}
        {...input}
      />
      {hint ? (
        <p id={hintId} className="text-[13px] text-ink-3">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
