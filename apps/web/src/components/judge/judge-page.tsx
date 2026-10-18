import { ArrowUpRight, Check, CircleSlash, FlaskConical, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { DocTable } from "@/components/site/doc-page";
import { cn } from "@/lib/utils";
import {
  ADOPTION,
  CRITERIA,
  REAL_VS_SIMULATED,
  REALITY_LABELS,
  WALKTHROUGH,
  type Criterion,
  type ProofLink,
  type Reality,
} from "./judge-content";

const REALITY_STYLE: Record<Reality, { icon: LucideIcon; className: string }> = {
  real: { icon: Check, className: "bg-pay-weak text-pay" },
  simulated: { icon: FlaskConical, className: "bg-esc-weak text-esc" },
  absent: { icon: CircleSlash, className: "bg-surface-3 text-ink-2" },
};

const PROOF_CLASS =
  "inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line-2 bg-surface px-3 py-1.5 text-[13px] font-semibold text-ink transition-colors hover:border-brand focus-visible:outline-2 focus-visible:outline-ring";

/** Internal routes go through the router; anchors and other sites are plain links. */
function SmartLink({ href, className, children }: { href: string; className?: string; children: ReactNode }) {
  if (href.startsWith("/")) {
    return (
      <Link href={href} className={className}>
        {children}
      </Link>
    );
  }
  return (
    <a href={href} className={className}>
      {children}
    </a>
  );
}

function Proof({ proof }: { proof: ProofLink }) {
  return (
    <span className="flex flex-col gap-1">
      <SmartLink href={proof.href} className={PROOF_CLASS}>
        {proof.label}
        <ArrowUpRight aria-hidden className="size-3.5 text-brand" />
      </SmartLink>
      {proof.hint ? <span className="max-w-[38ch] text-[12px] text-ink-3">{proof.hint}</span> : null}
    </span>
  );
}

function SectionHeading({ id, eyebrow, title, aside }: { id: string; eyebrow?: string; title: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow ? <p className="eyebrow text-brand">{eyebrow}</p> : null}
        <h2 id={id} className="font-serif mt-1 text-[26px] leading-tight font-semibold tracking-[-0.015em] text-ink sm:text-[30px]">
          {title}
        </h2>
      </div>
      {aside}
    </div>
  );
}

function RubricNav() {
  return (
    <nav aria-label="Criterios de la rúbrica" className="mt-8 flex flex-wrap gap-2">
      {CRITERIA.map((criterion) => (
        <a
          key={criterion.id}
          href={`#${criterion.id}`}
          className="inline-flex h-9 items-center gap-2 rounded-full border border-line bg-surface px-3.5 text-[13px] font-medium text-ink-2 transition-colors hover:border-brand hover:text-ink"
        >
          {criterion.title}
          <span className="tabular-nums font-semibold text-brand">{criterion.weight} %</span>
        </a>
      ))}
    </nav>
  );
}

function Walkthrough() {
  return (
    <section id="recorrido" aria-labelledby="recorrido-titulo" className="scroll-mt-20">
      <SectionHeading id="recorrido-titulo" eyebrow="Empieza aquí" title="Recorrido de 2 minutos" />
      <ol className="mt-5 grid gap-3 md:grid-cols-5">
        {WALKTHROUGH.map((step, index) => (
          <li key={step.title} className="card-surface flex flex-col gap-2 p-4">
            <span
              aria-hidden
              className="inline-flex size-7 items-center justify-center rounded-full bg-brand-weak text-[13px] font-semibold text-brand tabular-nums"
            >
              {index + 1}
            </span>
            <h3 className="text-[15px] font-semibold text-ink">{step.title}</h3>
            <p className="flex-1 text-[13.5px] leading-relaxed text-ink-2">{step.detail}</p>
            <SmartLink href={step.href} className="inline-flex items-center gap-1 text-[13px] font-semibold text-brand hover:underline">
              {step.action}
              <ArrowUpRight aria-hidden className="size-3.5" />
            </SmartLink>
          </li>
        ))}
      </ol>
    </section>
  );
}

function CriterionSection({ criterion }: { criterion: Criterion }) {
  const titleId = `${criterion.id}-titulo`;
  return (
    <section id={criterion.id} aria-labelledby={titleId} className="scroll-mt-20">
      <SectionHeading
        id={titleId}
        title={criterion.title}
        aside={
          <span className="inline-flex h-8 items-center rounded-full bg-brand-weak px-3 text-[14px] font-semibold text-brand tabular-nums">
            {criterion.weight} %
          </span>
        }
      />
      <p className="mt-1.5 text-[15px] text-ink-3 italic">{criterion.question}</p>
      <ul className="mt-5 grid gap-3">
        {criterion.claims.map((claim) => (
          <li
            key={claim.text}
            className="card-surface flex flex-col gap-3 p-4 sm:p-5 md:flex-row md:items-start md:justify-between md:gap-6"
          >
            <p className="text-[15px] leading-relaxed text-ink md:max-w-[62ch]">{claim.text}</p>
            <div className="flex flex-wrap gap-2 md:max-w-[22rem] md:shrink-0 md:justify-end">
              {claim.proofs.map((proof) => (
                <Proof key={proof.label} proof={proof} />
              ))}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function RealityPill({ status }: { status: Reality }) {
  const { icon: Icon, className } = REALITY_STYLE[status];
  return (
    <span className={cn("inline-flex h-6 items-center gap-1.5 rounded-full pr-2.5 pl-2 text-xs font-semibold whitespace-nowrap", className)}>
      <Icon aria-hidden className="size-3.5" strokeWidth={2.2} />
      {REALITY_LABELS[status]}
    </span>
  );
}

function RealVsSimulated() {
  return (
    <section id="real-vs-simulado" aria-labelledby="real-titulo" className="scroll-mt-20">
      <SectionHeading id="real-titulo" eyebrow="Sin adornos" title="Real vs. simulado" />
      <div className="card-surface mt-5 overflow-hidden">
        <DocTable>
          <table aria-labelledby="real-titulo" className="w-full text-left text-[14px]">
            <thead className="bg-surface-2 text-[12.5px] text-ink-3">
              <tr>
                <th scope="col" className="px-4 py-2.5 font-medium">Parte</th>
                <th scope="col" className="hidden px-4 py-2.5 font-medium sm:table-cell">Estado</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Qué significa</th>
              </tr>
            </thead>
            <tbody>
              {REAL_VS_SIMULATED.map((row) => (
                <tr key={row.part} className="border-t border-line align-top">
                  <th scope="row" className="w-[38%] px-4 py-3 font-semibold text-ink sm:w-auto">
                    {row.part}
                    <span className="mt-1.5 block sm:hidden">
                      <RealityPill status={row.status} />
                    </span>
                  </th>
                  <td className="hidden px-4 py-3 sm:table-cell">
                    <RealityPill status={row.status} />
                  </td>
                  <td className="px-4 py-3 text-ink-2">{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </DocTable>
      </div>
    </section>
  );
}

function Adoption() {
  return (
    <section id="adopcion" aria-labelledby="adopcion-titulo" className="scroll-mt-20">
      <SectionHeading id="adopcion-titulo" eyebrow="Viabilidad de implementación" title="Cómo lo adopta una empresa" />
      <p className="mt-1.5 max-w-[70ch] text-[15px] text-ink-2">
        Con datos del repositorio. Donde no hay medición, lo decimos: <b className="text-ink">NO MEDIDO</b>.
      </p>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {ADOPTION.map((item) => (
          <article key={item.title} className="card-surface flex flex-col gap-3 p-5">
            <h3 className="text-[16px] font-semibold text-ink">{item.title}</h3>
            <ul className="flex flex-1 list-disc flex-col gap-1.5 pl-5 text-[14px] leading-relaxed text-ink-2 marker:text-ink-3">
              {item.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
            {item.link ? (
              <div>
                <Proof proof={item.link} />
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export function JudgePage() {
  return (
    <article className="mx-auto flex max-w-6xl flex-col gap-14 px-4 pt-10 pb-16 sm:pt-14">
      <header>
        <p className="eyebrow text-brand">Para el jurado · Hackathon 30X, Reto Blinka</p>
        <h1 className="font-serif mt-2 max-w-[22ch] text-[34px] leading-tight font-semibold tracking-[-0.015em] text-ink sm:text-[44px]">
          Custodio, criterio por criterio
        </h1>
        <p className="mt-3 max-w-[68ch] text-[17px] text-ink-2">
          El reto: un agente que revise las cuentas por pagar, decida cuáles pagar dentro de las reglas de la empresa y pida
          permiso a una persona cuando algo se sale. Cada afirmación de esta página tiene al lado el enlace que la prueba en
          el producto, en un clic. Sin registro y sin dinero real.
        </p>
        <RubricNav />
      </header>
      <Walkthrough />
      {CRITERIA.map((criterion) => (
        <CriterionSection key={criterion.id} criterion={criterion} />
      ))}
      <Adoption />
      <RealVsSimulated />
    </article>
  );
}
