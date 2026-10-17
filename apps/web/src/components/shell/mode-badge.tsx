"use client";

import { FlaskConical } from "lucide-react";
import { useApiMode } from "@/components/providers/api-provider";

/** Says so whenever the numbers on screen are example data, not measurements. */
export function ModeBadge() {
  if (useApiMode() !== "mock") return null;
  return (
    <span className="inline-flex h-7 shrink-0 items-center whitespace-nowrap gap-1.5 rounded-full border border-line-2 bg-surface px-2.5 text-xs font-medium text-ink-2">
      <FlaskConical aria-hidden className="size-3.5 text-brand" />
      Datos de ejemplo
    </span>
  );
}
