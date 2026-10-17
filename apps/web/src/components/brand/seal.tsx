import { cn } from "@/lib/utils";

const ROSETTE_ANGLES = [0, 30, 60, 90, 120, 150];

/** The guilloche seal from the prototype: six rotated ellipses, the mark of a security print. */
export function Seal({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" aria-hidden className={cn("text-brand", className)}>
      <circle cx="20" cy="20" r="18.5" fill="none" stroke="currentColor" strokeWidth="1.2" opacity=".55" />
      <g fill="none" stroke="currentColor" strokeWidth="1.1">
        {ROSETTE_ANGLES.map((angle) => (
          <ellipse key={angle} cx="20" cy="20" rx="14" ry="5.2" transform={`rotate(${angle} 20 20)`} />
        ))}
      </g>
      <circle cx="20" cy="20" r="3.2" fill="currentColor" />
    </svg>
  );
}

export function Wordmark({ className, subtitle }: { className?: string; subtitle?: string }) {
  return (
    <span className={cn("flex items-center gap-2.5", className)}>
      <Seal className="size-8 shrink-0" />
      <span className="leading-none">
        <span className="font-display block text-[19px] font-semibold tracking-[-0.01em]">Custodio</span>
        {subtitle ? <span className="mt-1 block text-[11.5px] text-ink-3">{subtitle}</span> : null}
      </span>
    </span>
  );
}
