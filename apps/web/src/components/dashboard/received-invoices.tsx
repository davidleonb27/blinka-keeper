"use client";

import { Inbox, Scale } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/errors";
import { useProcessInvoices } from "@/lib/api/hooks";

/** Invoices the workspace received and Custodio has not decided yet; one click runs them through the rules. */
export function ReceivedInvoices({ count }: { count: number }) {
  const process = useProcessInvoices();
  const one = count === 1;
  // A promise, not mutate callbacks: this banner unmounts as soon as the refreshed summary has nothing pending,
  // and React Query drops the callbacks of an unmounted caller.
  const decide = () =>
    process.mutateAsync().then(
      ({ batch }) => toast.success(`Custodio decidió ${batch.metrics.total} ${batch.metrics.total === 1 ? "factura" : "facturas"}.`),
      (error: unknown) => toast.error(messageOf(error)),
    );
  return (
    <section aria-label="Facturas por decidir" className="card-surface flex flex-wrap items-center gap-x-4 gap-y-3 p-5">
      <Inbox aria-hidden className="size-6 shrink-0 text-brand" />
      <p className="min-w-0 flex-1 text-ink-2">
        <b className="font-semibold text-ink">
          {count} {one ? "factura recibida" : "facturas recibidas"}
        </b>{" "}
        {one ? "espera" : "esperan"} que Custodio {one ? "la decida" : "las decida"} con tus reglas: pagar, retener o
        pedirte permiso.
      </p>
      <Button onClick={() => void decide()} disabled={process.isPending}>
        <Scale aria-hidden /> {one ? "Decidir la factura" : `Decidir las ${count} facturas`}
      </Button>
    </section>
  );
}
