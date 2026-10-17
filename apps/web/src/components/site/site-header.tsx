import Link from "next/link";
import { Wordmark } from "@/components/brand/seal";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { Button } from "@/components/ui/button";
import { GitHubLink } from "./github-link";

const NAV = [
  { href: "/#funciones", label: "Funciones" },
  { href: "/docs", label: "Documentación" },
  { href: "/docs/inicio-rapido#autoalojado", label: "Autoalojar" },
  { href: "/reto", label: "Seguridad" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-background/80 pt-[env(safe-area-inset-top)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4">
        <div className="flex min-w-0 items-center gap-6">
          <Link href="/" aria-label="Custodio, inicio" className="rounded-lg">
            <Wordmark />
          </Link>
          <nav aria-label="Principal" className="hidden items-center gap-0.5 text-[14px] font-medium text-ink-2 lg:flex">
            {NAV.map(({ href, label }) => (
              <Link key={href} href={href} className="rounded-lg px-3 py-2 transition-colors hover:text-ink">
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-1.5">
          <Link href="/docs" className="rounded-lg px-2 py-2 text-[14px] font-medium text-ink-2 hover:text-ink lg:hidden">
            Docs
          </Link>
          <GitHubLink className="hidden sm:inline-flex" />
          <ThemeToggle />
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <Link href="/panel">Probar la demo</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
