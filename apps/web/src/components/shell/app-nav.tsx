"use client";

import {
  Building2,
  CalendarClock,
  Code2,
  HandCoins,
  Landmark,
  Gauge,
  LayoutGrid,
  Link2,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Wordmark } from "@/components/brand/seal";
import { SETUP_LABEL, SETUP_PATH } from "@/components/landing/use-company-button";
import { SUPPLIERS_PATH } from "@/components/suppliers/unknown-supplier-hint";
import { useWorkspaceSummary } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { ModeBadge } from "./mode-badge";
import { ThemeToggle } from "./theme-toggle";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/panel", label: "Panel", icon: LayoutGrid },
  { href: "/autonomia", label: "Autonomía", icon: Gauge },
  { href: "/calendario", label: "Calendario", icon: CalendarClock },
  { href: "/pagos", label: "Pagos", icon: HandCoins },
  { href: "/conciliacion", label: "Conciliación", icon: Landmark },
  { href: "/reglas", label: "Reglas", icon: SlidersHorizontal },
  { href: SUPPLIERS_PATH, label: "Proveedores", icon: Users },
  { href: "/registro", label: "Registro", icon: Link2 },
  { href: "/desarrolladores", label: "Desarrolladores", icon: Code2 },
  { href: SETUP_PATH, label: SETUP_LABEL, icon: Building2 },
  { href: "/reto", label: "Seguridad", icon: ShieldCheck },
];

function PendingBadge() {
  const pending = useWorkspaceSummary().data?.metrics.pending ?? 0;
  if (!pending) return null;
  return (
    <span className="ml-auto grid h-5 min-w-[22px] place-items-center rounded-full bg-esc px-1.5 text-[11.5px] font-bold text-surface tabular">
      {pending}
      <span className="sr-only"> esperan aprobación</span>
    </span>
  );
}

function NavLinks({ layout }: { layout: "rail" | "strip" }) {
  const pathname = usePathname();
  return (
    <ul className={cn("flex gap-0.5", layout === "rail" ? "flex-col" : "flex-row")}>
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const current = pathname === href || (href === "/reto" && pathname === "/arena");
        return (
          <li key={href}>
            <Link
              href={href}
              aria-current={current ? "page" : undefined}
              className={cn(
                "flex h-10 items-center gap-2.5 rounded-[10px] px-2.5 font-medium whitespace-nowrap text-ink-2 hover:bg-surface-2 hover:text-ink",
                current && "bg-brand-weak text-ink [&>svg]:text-brand",
              )}
            >
              <Icon aria-hidden className="size-[18px] shrink-0" strokeWidth={1.75} />
              {label}
              {href === "/panel" && layout === "rail" ? <PendingBadge /> : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function CompanyFooter() {
  const company = useWorkspaceSummary().data?.company_name;
  return (
    <div className="mt-auto flex flex-col gap-2.5 border-t border-line px-2 pt-3">
      <div>
        <b className="block font-semibold">{company ?? "Tu empresa"}</b>
        <span className="text-xs text-ink-3">Espacio de trabajo</span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <ModeBadge />
        <ThemeToggle />
      </div>
    </div>
  );
}

export function AppNav() {
  return (
    <>
      <aside className="sticky top-4 my-4 hidden h-[calc(100dvh-2rem)] min-h-[520px] flex-col gap-5 self-start rounded-[18px] border border-line bg-surface px-3 pt-[18px] pb-3.5 lg:flex">
        <Link href="/" className="rounded-lg px-1.5" aria-label="Custodio, inicio">
          <Wordmark subtitle="Agente de pagos" />
        </Link>
        <nav aria-label="Secciones">
          <NavLinks layout="rail" />
        </nav>
        <CompanyFooter />
      </aside>
      <header className="sticky top-0 z-40 -mx-4 border-b border-line bg-background/85 px-4 pt-[max(0.5rem,env(safe-area-inset-top))] backdrop-blur-md lg:hidden">
        <div className="flex h-12 items-center justify-between gap-3">
          <Link href="/" aria-label="Custodio, inicio" className="rounded-lg">
            <Wordmark />
          </Link>
          <div className="flex items-center gap-1">
            <ModeBadge />
            <ThemeToggle />
          </div>
        </div>
        <nav aria-label="Secciones" className="-mx-4 overflow-x-auto px-4 pb-2 [scrollbar-width:none]">
          <NavLinks layout="strip" />
        </nav>
      </header>
    </>
  );
}
