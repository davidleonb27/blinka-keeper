"use client";

import { RotateCw, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { messageOf } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  return (
    <div role="alert" className={cn("card-surface flex flex-col items-start gap-3 p-5", className)}>
      <p className="flex items-center gap-2 font-semibold">
        <TriangleAlert aria-hidden className="size-4 text-esc" />
        No pudimos cargar esto
      </p>
      <p className="max-w-[60ch] text-ink-2">{messageOf(error)}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw aria-hidden /> Reintentar
        </Button>
      ) : null}
    </div>
  );
}

export function LoadingBlock({ className, label = "Cargando…" }: { className?: string; label?: string }) {
  return (
    <div role="status" aria-label={label} className={cn("card-surface p-5", className)}>
      <Skeleton className="mb-3 h-4 w-1/3" />
      <Skeleton className="mb-2 h-8 w-1/2" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

export function Meter({ value, tone = "brand", label }: { value: number; tone?: "brand" | "pay" | "esc"; label: string }) {
  const percent = Math.max(0, Math.min(100, value * 100));
  const fill = { brand: "bg-brand", pay: "bg-pay", esc: "bg-esc" }[tone];
  const track = { brand: "bg-brand-weak", pay: "bg-pay-weak", esc: "bg-esc-weak" }[tone];
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(percent)}
      className={cn("h-1.5 overflow-hidden rounded-full", track)}
    >
      <i className={cn("block h-full rounded-full transition-[width] duration-700", fill)} style={{ width: `${percent}%` }} />
    </div>
  );
}
