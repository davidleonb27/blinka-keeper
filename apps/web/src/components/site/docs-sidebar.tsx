"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { docsGroups } from "@/lib/docs";
import { cn } from "@/lib/utils";

/** One navigation: a scrollable row of links on phones, a sticky sidebar from the large breakpoint up. */
export function DocsSidebar() {
  const pathname = usePathname();
  const navRef = useRef<HTMLElement>(null);
  // On phones the row scrolls sideways; bring the current page into view without moving the page itself.
  useEffect(() => {
    const nav = navRef.current;
    const current = nav?.querySelector<HTMLElement>('[aria-current="page"]');
    if (nav && current && nav.scrollWidth > nav.clientWidth) {
      nav.scrollLeft = current.offsetLeft - (nav.clientWidth - current.offsetWidth) / 2;
    }
  }, [pathname]);
  return (
    <nav
      ref={navRef}
      aria-label="Documentación"
      className="-mx-4 overflow-x-auto border-b border-line px-4 py-3 lg:sticky lg:top-16 lg:mx-0 lg:max-h-[calc(100dvh-4rem)] lg:overflow-y-auto lg:border-0 lg:px-0 lg:py-8"
    >
      <div className="flex gap-1 lg:flex-col lg:gap-6">
        {docsGroups().map(({ group, pages }) => (
          <div key={group} className="contents lg:block">
            <p className="eyebrow mb-2 hidden lg:block">{group}</p>
            <ul className="contents lg:flex lg:flex-col lg:gap-0.5">
              {pages.map((page) => {
                const current = page.href === pathname;
                return (
                  <li key={page.href} className="shrink-0">
                    <Link
                      href={page.href}
                      aria-current={current ? "page" : undefined}
                      className={cn(
                        "block rounded-lg px-3 py-1.5 text-[14px] whitespace-nowrap transition-colors",
                        current ? "bg-brand-weak font-semibold text-brand" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
                      )}
                    >
                      {page.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
