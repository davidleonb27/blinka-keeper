import { Check, Minus, OctagonMinus, UserRound, type LucideIcon } from "lucide-react";
import type { RuleOutcome, RuleResult } from "@/lib/api/contracts";
import { cn } from "@/lib/utils";

const OUTCOME_STYLE: Record<RuleOutcome, { icon: LucideIcon; row: string; badge: string; label: string }> = {
  pass: { icon: Check, row: "", badge: "bg-pay-weak text-pay", label: "Cumple" },
  skipped: { icon: Minus, row: "text-ink-3", badge: "bg-surface-3 text-ink-3", label: "No aplica" },
  hold: { icon: OctagonMinus, row: "bg-hold-weak", badge: "bg-hold text-surface", label: "Retiene" },
  escalate: { icon: UserRound, row: "bg-esc-weak", badge: "bg-esc text-surface", label: "Pide permiso" },
};

export function RuleList({ rules }: { rules: RuleResult[] }) {
  return (
    <ul aria-label="Reglas evaluadas" className="overflow-hidden rounded-xl border border-line">
      {rules.map((rule) => {
        const style = OUTCOME_STYLE[rule.outcome];
        const Icon = style.icon;
        return (
          <li
            key={rule.rule_id}
            className={cn("grid grid-cols-[22px_34px_minmax(0,1fr)] items-start gap-2 px-3 py-2.5 [&+&]:border-t [&+&]:border-line", style.row)}
          >
            <span className={cn("grid size-[22px] place-items-center rounded-full", style.badge)}>
              <Icon aria-hidden className="size-3" strokeWidth={2.6} />
              <span className="sr-only">{style.label}</span>
            </span>
            <span className="pt-0.5 font-mono text-[11.5px] text-ink-3">{rule.rule_id}</span>
            <div className="min-w-0">
              <strong className={cn("text-[13px] font-semibold", rule.outcome === "skipped" && "text-ink-3")}>
                {rule.label}
              </strong>
              <p className={cn("mt-px text-[12.5px]", rule.outcome === "skipped" ? "text-ink-3" : "text-ink-2")}>
                {rule.reason}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
