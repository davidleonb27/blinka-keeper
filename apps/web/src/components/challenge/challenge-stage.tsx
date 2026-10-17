"use client";

import { useSyncExternalStore } from "react";
import { ErrorState, LoadingBlock } from "@/components/states";
import type { ChallengeAttempt, ChallengeStats } from "@/lib/api/contracts";
import { useChallengeStats } from "@/lib/api/hooks";
import { formatCount, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { attemptVerdict, latestAttempt, VERDICT_TEXT } from "./attempt-verdict";
import { QrCode } from "./qr-code";

/** On stage the room watches the numbers move, so they refresh faster than on the attacker's page. */
const STAGE_POLL_MS = 3_000;
const CHALLENGE_PATH = "/reto";

const noSubscription = () => () => {};

/** The public URL is whatever host served this page, known only in the browser; the server renders a placeholder. */
function useSiteOrigin(): string | null {
  return useSyncExternalStore(
    noSubscription,
    () => window.location.origin,
    () => null,
  );
}

function StageQr() {
  const origin = useSiteOrigin();
  const box = "w-full max-w-[min(100%,62vh,560px)]";
  if (!origin) return <div aria-hidden className={cn(box, "aspect-square rounded-xl bg-surface-3")} />;
  const url = `${origin}${CHALLENGE_PATH}`;
  return (
    <>
      <QrCode value={url} className={box} />
      <p className="font-mono text-[15px] font-semibold break-all sm:text-[18px]">{url.replace(/^https?:\/\//, "")}</p>
    </>
  );
}

function StageCounter({ label, value, tone }: { label: string; value: number; tone?: "good" }) {
  return (
    <div className="rounded-xl border border-line px-3 py-3">
      <span className="block text-[13px] text-ink-3">{label}</span>
      <b className={cn("text-[28px] leading-tight font-semibold tabular sm:text-[34px]", tone === "good" && "text-pay")}>{formatCount(value)}</b>
    </div>
  );
}

function StageScoreboard({ stats }: { stats: ChallengeStats }) {
  const broken = stats.improper_payments > 0;
  return (
    <section aria-label="Contador en vivo" className="flex flex-col gap-3">
      <div
        role="status"
        aria-label="Pagos indebidos"
        className={cn("rounded-2xl px-5 py-4", broken ? "bg-crit-weak" : "bg-pay-weak")}
      >
        <span className="block text-[18px] font-semibold text-ink-2 sm:text-[22px]">Pagos indebidos</span>
        <b className={cn("block text-[88px] leading-none font-semibold tracking-[-0.04em] tabular sm:text-[132px]", broken ? "text-crit" : "text-pay")}>
          {formatCount(stats.improper_payments)}
        </b>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <StageCounter label="Intentos" value={stats.attempts} />
        <StageCounter label="Frenados" value={stats.held} />
        <StageCounter label="Escalados" value={stats.escalated} />
        <StageCounter label="Pagos legítimos" value={stats.paid_legitimately} tone="good" />
      </div>
    </section>
  );
}

function LatestAttempt({ attempt }: { attempt: ChallengeAttempt }) {
  const verdict = attemptVerdict(attempt);
  return (
    <section aria-label="Último intento" className="card-surface flex flex-col gap-1 p-5">
      <span className="text-[13px] text-ink-3">Último intento en el muro</span>
      <b className="text-[18px] font-semibold break-words">{attempt.technique ?? "Técnica sin nombre"}</b>
      <span className="text-[13px] text-ink-3">
        {attempt.alias ?? "Anónimo"} · {formatDateTime(attempt.at)}
      </span>
      <b className={cn("mt-1 text-[22px] font-semibold", VERDICT_TEXT[verdict.tone])}>{verdict.headline}</b>
    </section>
  );
}

function StageNumbers() {
  const stats = useChallengeStats(STAGE_POLL_MS);
  if (stats.error) return <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />;
  if (!stats.data) return <LoadingBlock label="Cargando el contador…" />;
  const latest = latestAttempt(stats.data.hall_of_fame);
  return (
    <>
      <StageScoreboard stats={stats.data} />
      {latest ? <LatestAttempt attempt={latest} /> : null}
    </>
  );
}

/** /reto?escenario=1: projected during the demo so the jury can scan in and attack from their phones. */
export function ChallengeStage() {
  return (
    <div className="grid grid-cols-1 items-start gap-6 pt-2 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <section aria-label="Entra al reto" className="flex flex-col items-center gap-3 text-center">
        <h1 className="font-serif text-[30px] leading-[1.1] font-semibold tracking-[-0.02em] sm:text-[44px]">Róbale a Custodio</h1>
        <p className="max-w-[40ch] text-[16px] text-ink-2 sm:text-[18px]">Escanea, escribe una factura trampa e intenta que pague algo indebido.</p>
        <StageQr />
      </section>
      <div className="flex flex-col gap-4">
        <StageNumbers />
      </div>
    </div>
  );
}
