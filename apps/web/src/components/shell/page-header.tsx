import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, children }: { title: string; subtitle: string; children?: ReactNode }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pt-2 pb-5">
      <div className="min-w-0">
        <h1 className="font-display text-[26px] leading-[1.1] font-semibold tracking-[-0.02em] sm:text-[30px]">{title}</h1>
        <p className="mt-1.5 max-w-[62ch] text-ink-2">{subtitle}</p>
      </div>
      {children ? <div className="flex flex-wrap gap-2">{children}</div> : null}
    </header>
  );
}

export function Chip({ children, tone = "plain" }: { children: ReactNode; tone?: "plain" | "ok" | "bad" | "live" }) {
  const tones = {
    plain: "border-line-2 bg-surface text-ink-2",
    ok: "border-transparent bg-pay-weak text-pay font-semibold",
    bad: "border-transparent bg-crit-weak text-crit font-semibold",
    live: "border-line-2 bg-surface text-ink-2 before:size-[7px] before:rounded-full before:bg-brand before:content-['']",
  };
  return (
    <span className={`inline-flex h-[30px] items-center gap-1.5 rounded-full border px-3 text-[12.5px] whitespace-nowrap ${tones[tone]}`}>
      {children}
    </span>
  );
}
