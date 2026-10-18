"use client";

import { useEffect, useState } from "react";

const TICK_MS = 1_000;
const SECONDS_PER_MINUTE = 60;

/** Seconds since `iso`, kept current. Rendered only after the API answered, so never during hydration. */
function useSecondsSince(iso: string): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);
  return Math.max(0, Math.round((now - Date.parse(iso)) / TICK_MS));
}

export function ago(seconds: number): string {
  if (seconds < SECONDS_PER_MINUTE) return `hace ${seconds} s`;
  return `hace ${Math.floor(seconds / SECONDS_PER_MINUTE)} min`;
}

/** «Verificado en Stripe hace 3 s»: how fresh Stripe's answer is. */
export function Freshness({ checkedAt, label = "Verificado en Stripe" }: { checkedAt: string; label?: string }) {
  const seconds = useSecondsSince(checkedAt);
  return (
    <span className="text-[12.5px] text-ink-3">
      {label} {ago(seconds)}
    </span>
  );
}
