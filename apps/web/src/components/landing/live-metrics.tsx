"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useChallengeStats, useWorkspaceSummary } from "@/lib/api/hooks";
import { formatCount, formatPercent, NOT_MEASURED } from "@/lib/format";
import { cn } from "@/lib/utils";

function Metric({ label, value, detail, tone }: { label: string; value: string | null; detail: string; tone?: "good" | "bad" }) {
  return (
    <div className="flex min-w-0 flex-col gap-1.5 px-5 py-5 sm:px-6">
      <dt className="text-[13px] font-medium text-ink-2">{label}</dt>
      <dd
        className={cn(
          "text-[40px] leading-none font-semibold tracking-[-0.03em] tabular sm:text-[48px]",
          value === NOT_MEASURED && "text-2xl sm:text-2xl",
          tone === "good" && "text-pay",
          tone === "bad" && "text-crit",
        )}
      >
        {value ?? <Skeleton className="h-10 w-24" />}
      </dd>
      <dd className="text-[12.5px] text-ink-3">{detail}</dd>
    </div>
  );
}

/** The three numbers Blinka judges, straight from the API. A failed read says NO MEDIDO, never zero. */
export function LiveMetrics() {
  const summary = useWorkspaceSummary();
  const challenge = useChallengeStats();
  const metrics = summary.data?.metrics;
  const stats = challenge.data;

  const autonomy = metrics ? formatPercent(metrics.autonomy_rate) : summary.error ? NOT_MEASURED : null;
  const improperCount = metrics && stats ? metrics.improper_payments + stats.improper_payments : null;
  const improper =
    improperCount !== null ? formatCount(improperCount) : summary.error || challenge.error ? NOT_MEASURED : null;
  const attacks = stats ? formatCount(stats.attempts) : challenge.error ? NOT_MEASURED : null;

  return (
    <dl className="card-surface grid grid-cols-1 divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
      <Metric
        label="Autonomía"
        value={autonomy}
        detail={
          metrics
            ? `${metrics.paid_auto + metrics.hold} de ${metrics.total} facturas decididas sin una persona`
            : "Facturas decididas sin una persona"
        }
      />
      <Metric
        label="Pagos indebidos"
        value={improper}
        detail="En el panel y en el reto público. Uno solo descalifica."
        tone={improperCount === null ? undefined : improperCount === 0 ? "good" : "bad"}
      />
      <Metric label="Ataques probados" value={attacks} detail="Intentos en «Róbale a Custodio», todos con su acta." />
    </dl>
  );
}
