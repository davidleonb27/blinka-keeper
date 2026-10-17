import { Check, OctagonMinus, UserCheck, UserRound, X, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DecisionStatus } from "@/lib/api/contracts";
import { STATUS_META, type Tone } from "@/lib/presentation";

const ICONS: Record<DecisionStatus, LucideIcon> = {
  paid_auto: Check,
  paid_human: UserCheck,
  hold: OctagonMinus,
  pending_approval: UserRound,
  rejected: X,
};

export const TONE_CLASSES: Record<Tone, string> = {
  pay: "bg-pay-weak text-pay",
  hold: "bg-hold-weak text-hold",
  esc: "bg-esc-weak text-esc",
  muted: "bg-surface-3 text-ink-2",
};

export function StatusPill({ status, size = "md" }: { status: DecisionStatus; size?: "md" | "lg" }) {
  const { label, tone } = STATUS_META[status];
  const Icon = ICONS[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold whitespace-nowrap",
        size === "lg" ? "h-8 pr-3 pl-2.5 text-[13px]" : "h-6 pr-2.5 pl-2 text-xs",
        TONE_CLASSES[tone],
      )}
    >
      <Icon aria-hidden className={size === "lg" ? "size-4" : "size-3.5"} strokeWidth={2.2} />
      {label}
    </span>
  );
}
