import { ArrowRight, CircleHelp, MessageSquareQuote, Sparkles } from "lucide-react";
import type { PolicyChange, PolicyProposal } from "@/lib/api/contracts";
import { formatMoney, formatNumber } from "@/lib/format";

const PERCENT_FIELDS = new Set(["agreement_tolerance_pct"]);
const RATIO_FIELDS = new Set(["min_confidence"]);
const DAY_FIELDS = new Set(["duplicate_window_days", "split_window_days"]);

export function formatPolicyValue(change: Pick<PolicyChange, "field">, value: unknown, currency: string): string {
  if (typeof value === "boolean") return value ? "Permitido" : "Bloqueado";
  if (typeof value !== "number") return value == null ? "—" : String(value);
  if (PERCENT_FIELDS.has(change.field)) return `${formatNumber(value, 1)} %`;
  if (RATIO_FIELDS.has(change.field)) return `${formatNumber(value * 100)} %`;
  if (DAY_FIELDS.has(change.field)) return `${value} días`;
  return formatMoney(value, currency);
}

/** What the compiler understood, what it could not map and what it needs to ask. Never a guess. */
export function ProposalView({ proposal, currency }: { proposal: PolicyProposal; currency: string }) {
  return (
    <div className="flex flex-col gap-3" aria-live="polite">
      {proposal.changes.length ? (
        <section className="card-surface p-4">
          <h2 className="mb-3 flex items-center gap-2 text-[14px] font-semibold">
            <Sparkles aria-hidden className="size-4 text-brand" /> Así lo entendió Blinka Keeper
          </h2>
          <ul className="flex flex-col gap-2.5">
            {proposal.changes.map((change) => (
              <li key={change.field} className="rounded-xl border border-line p-3">
                <p className="font-semibold">{change.label}</p>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-[14px] tabular">
                  <span className="text-ink-3 line-through decoration-ink-3/50">
                    {formatPolicyValue(change, change.before, currency)}
                  </span>
                  <ArrowRight aria-label="pasa a" className="size-3.5 text-ink-3" />
                  <b className="text-brand">{formatPolicyValue(change, change.after, currency)}</b>
                </p>
                <p className="mt-1.5 flex gap-1.5 text-[12.5px] text-ink-3">
                  <MessageSquareQuote aria-hidden className="mt-0.5 size-3.5 shrink-0" />
                  «{change.source_quote}»
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {proposal.unsupported.map((text) => (
        <p key={text} className="rounded-xl bg-esc-weak px-3.5 py-2.5 text-[13.5px]">
          <b className="text-esc">No lo entendí, así que no cambia nada: </b>«{text}»
        </p>
      ))}
      {proposal.questions.map((question) => (
        <p key={question} className="flex gap-2 rounded-xl bg-brand-weak px-3.5 py-2.5 text-[13.5px]">
          <CircleHelp aria-hidden className="mt-0.5 size-4 shrink-0 text-brand" />
          {question}
        </p>
      ))}
    </div>
  );
}
