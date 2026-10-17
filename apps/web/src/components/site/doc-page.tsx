import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { docsPage, neighbours } from "@/lib/docs";

/** A documentation page: its title from the docs index, a lead, the text and links to the previous and next page. */
export function DocPage({ href, lead, children }: { href: string; lead: string; children: ReactNode }) {
  const page = docsPage(href);
  const { previous, next } = neighbours(href);
  return (
    <article className="max-w-[72ch] pb-16">
      <p className="eyebrow text-brand">{page.group}</p>
      <h1 className="font-display mt-2 text-[34px] leading-tight font-semibold tracking-[-0.025em] text-ink sm:text-[40px]">
        {page.title}
      </h1>
      <p className="mt-3 text-[17px] text-ink-2">{lead}</p>
      <div className="doc-prose mt-8">{children}</div>
      <nav aria-label="Páginas vecinas" className="mt-14 grid grid-cols-1 gap-3 border-t border-line pt-6 sm:grid-cols-2">
        {previous ? (
          <Link href={previous.href} className="rounded-xl border border-line p-4 transition-colors hover:border-brand">
            <span className="flex items-center gap-1 text-[12.5px] text-ink-3">
              <ArrowLeft aria-hidden className="size-3.5" /> Anterior
            </span>
            <span className="mt-1 block font-semibold text-ink">{previous.title}</span>
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link href={next.href} className="rounded-xl border border-line p-4 text-right transition-colors hover:border-brand">
            <span className="flex items-center justify-end gap-1 text-[12.5px] text-ink-3">
              Siguiente <ArrowRight aria-hidden className="size-3.5" />
            </span>
            <span className="mt-1 block font-semibold text-ink">{next.title}</span>
          </Link>
        ) : null}
      </nav>
    </article>
  );
}

/** A table that scrolls inside itself on narrow screens instead of widening the page. */
export function DocTable({ children }: { children: ReactNode }) {
  return (
    <div tabIndex={0} role="group" aria-label="Tabla desplazable" className="overflow-x-auto">
      {children}
    </div>
  );
}
