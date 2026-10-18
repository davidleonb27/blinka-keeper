"use client";

import { Check, X } from "lucide-react";
import Link from "next/link";
import { useHydrated } from "@/lib/hydration";
import { setTourDismissed, useTour, type TourStep } from "@/lib/tour";
import { cn } from "@/lib/utils";

interface Step {
  key: TourStep;
  label: string;
  href: string;
  optional?: boolean;
}

function stepsFor(firstActa: string | null): Step[] {
  return [
    { key: "decide", label: "Decidir las facturas", href: "/panel#facturas-por-decidir" },
    { key: "acta", label: "Abrir un acta", href: firstActa ? `/panel?acta=${encodeURIComponent(firstActa)}` : "/panel#facturas-title" },
    { key: "rule", label: "Ajustar una regla", href: "/reglas" },
    { key: "reconcile", label: "Conciliar el banco", href: "/conciliacion" },
    { key: "verify", label: "Verificar el registro", href: "/registro" },
    { key: "steal", label: "Intenta robarle", href: "/reto", optional: true },
  ];
}

/** A compact, dismissible walk through the value. Each step checks itself when it happens. */
export function GuidedTour({ decided, firstActa }: { decided: boolean; firstActa: string | null }) {
  const hydrated = useHydrated();
  const tour = useTour();
  if (!hydrated || tour.dismissed) return null;
  const done = new Set<TourStep>(tour.done);
  if (decided) done.add("decide");
  const steps = stepsFor(firstActa);
  const required = steps.filter((step) => !step.optional);
  const completed = required.filter((step) => done.has(step.key)).length;
  return (
    <section aria-labelledby="recorrido-title" className="card-surface p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="recorrido-title" className="font-semibold">Recorrido en 5 pasos</h2>
          <p className="text-[12.5px] text-ink-3">
            {completed === required.length ? "Recorrido completo: ya viste todo lo que hace Blinka Keeper." : `${completed} de ${required.length} hechos.`}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setTourDismissed(true)}
          aria-label="Ocultar el recorrido"
          className="rounded-md p-1 text-ink-3 hover:bg-surface-2 hover:text-ink"
        >
          <X aria-hidden className="size-4" />
        </button>
      </div>
      <ol className="mt-3 flex flex-wrap gap-2">
        {steps.map((step, index) => {
          const isDone = done.has(step.key);
          return (
            <li key={step.key}>
              <Link
                href={step.href}
                scroll={step.key === "decide"}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-medium transition-colors",
                  isDone ? "border-transparent bg-pay-weak text-pay" : "border-line-2 text-ink-2 hover:border-brand hover:text-ink",
                )}
              >
                {isDone ? <Check aria-hidden className="size-3.5" /> : <span aria-hidden className="tabular text-ink-3">{step.optional ? "+" : index + 1}</span>}
                {step.label}
                {step.optional ? <span className="text-ink-3">(opcional)</span> : null}
                <span className="sr-only">{isDone ? " · hecho" : " · pendiente"}</span>
              </Link>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
