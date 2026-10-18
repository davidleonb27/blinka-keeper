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
  { href: "/jurado", label: "Jurado" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-(--header) pt-[env(safe-area-inset-top)] backdrop-blur-[14px]">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4">
        <div className="flex min-w-0 items-center gap-6">
          <Link href="/" aria-label="Blinka Keeper, inicio" className="rounded-lg">
            <Wordmark />
          </Link>
          <nav aria-label="Principal" className="hidden items-center gap-1 text-[13px] text-ink-2 lg:flex">
            {NAV.map(({ href, label }) => (
              <Link key={href} href={href} className="rounded-md px-2.5 py-1.5 transition-colors duration-[160ms] hover:text-ink hover:underline hover:underline-offset-4">
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-1.5">
          <Link href="/docs" className="rounded-md px-2 py-2 text-[13px] text-ink-2 hover:text-ink lg:hidden">
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
