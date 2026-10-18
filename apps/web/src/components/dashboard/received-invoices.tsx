"use client";

import { Inbox, Scale } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/errors";
import { useProcessInvoices } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";

const CHANNELS = "correo, PDF, foto, WhatsApp";
const PROGRESS_STEPS = ["Leyendo cada documento", "Revisando las quince reglas", "Pagando lo que cumple", "Recalculando con el auditor"];
const PROGRESS_STEP_MS = 1_400;

/** Invoices the workspace received and Blinka Keeper has not decided yet; one click runs them through the rules. */
export function ReceivedInvoices({ count, first = false }: { count: number; first?: boolean }) {
  const process = useProcessInvoices();
  const one = count === 1;
  // A promise, not mutate callbacks: this banner unmounts as soon as the refreshed summary has nothing pending,
  // and React Query drops the callbacks of an unmounted caller.
  const decide = () =>
    process.mutateAsync().then(
      ({ batch }) => toast.success(`Blinka Keeper decidió ${batch.metrics.total} ${batch.metrics.total === 1 ? "factura" : "facturas"}.`),
      (error: unknown) => toast.error(messageOf(error)),
    );
  return (
    <section
      id="facturas-por-decidir"
      aria-label="Facturas por decidir"
      className={cn("card-surface flex flex-col gap-4 p-5 sm:flex-row sm:items-center", first && "sm:p-7")}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <Inbox aria-hidden className={cn("shrink-0 text-brand", first ? "mt-1 size-7" : "size-6")} />
        <div className="min-w-0">
          <p className={cn("font-semibold text-ink", first ? "text-[19px] leading-snug sm:text-[22px]" : "text-[15px]")}>
            {count} {one ? "factura recibida" : "facturas recibidas"}
            {first ? `: ${CHANNELS}` : null}
          </p>
          <p className="mt-1 text-ink-2">
            {first
              ? "Blinka Keeper las lee, las pasa por tus quince reglas y paga lo que cumple. Lo que importa te lo pide a ti."
              : `${one ? "Espera" : "Esperan"} que Blinka Keeper ${one ? "la decida" : "las decida"} con tus reglas: pagar, retener o pedirte permiso.`}
          </p>
          {process.isPending ? <DecidingProgress count={count} /> : null}
        </div>
      </div>
      <Button onClick={() => void decide()} disabled={process.isPending} className={cn("self-start sm:self-center", first && "h-12 px-6 text-base")}>
        <Scale aria-hidden /> {process.isPending ? "Decidiendo…" : one ? "Decidir la factura" : `Decidir las ${count} facturas`}
      </Button>
    </section>
  );
}

function DecidingProgress({ count }: { count: number }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setStep((current) => Math.min(current + 1, PROGRESS_STEPS.length - 1)), PROGRESS_STEP_MS);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div role="status" className="mt-3">
      <p className="text-[13px] font-medium text-ink-2">
        {PROGRESS_STEPS[step]}… ({count} {count === 1 ? "factura" : "facturas"})
      </p>
      <div className="mt-1.5 h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-brand transition-[width] duration-700 ease-out"
          style={{ width: `${((step + 1) / (PROGRESS_STEPS.length + 1)) * 100}%` }}
        />
      </div>
    </div>
  );
}
