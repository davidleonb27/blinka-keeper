import {
  ArrowRight,
  BookOpenCheck,
  Bot,
  Building2,
  Code2,
  FileSearch,
  Link2,
  MessagesSquare,
  MousePointerClick,
  Scale,
  Swords,
  Target,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { Wordmark } from "@/components/brand/seal";
import { ActaPreview } from "@/components/landing/acta-preview";
import { LiveMetrics } from "@/components/landing/live-metrics";
import { ModeBadge } from "@/components/shell/mode-badge";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { Button } from "@/components/ui/button";
import { RAIL_PITCH } from "@/lib/presentation";

const FLOW: { title: string; tag: string; text: string; icon: LucideIcon; person?: boolean }[] = [
  { title: "Lee", tag: "Modelo", icon: FileSearch, text: "Saca quién cobra, cuánto, en qué moneda y a qué cuenta, y cita de dónde lo leyó." },
  { title: "Decide", tag: "Código", icon: Scale, text: "Doce reglas escritas en código revisan cada factura. El modelo no decide ni hace cuentas." },
  { title: "Explica", tag: "Acta", icon: BookOpenCheck, text: "Cada decisión queda en un acta que se entiende sin abrir el código." },
  { title: "Pide permiso", tag: "Persona", icon: UserCheck, text: "Lo que se sale de las reglas espera el sí de una persona.", person: true },
];

const FEATURES: { title: string; text: string; icon: LucideIcon; href: string }[] = [
  { title: "Firewall de pagos para cualquier agente", icon: Bot, href: "/desarrolladores", text: "Otro agente envía una intención de pago por API o MCP y recibe pagar, retener o escalar, con su acta." },
  { title: "Claude contra Claude", icon: Swords, href: "/arena", text: "Un atacante genera facturas fraudulentas contra tus reglas y cambia de técnica. El defensor no cambia: las reglas son código." },
  { title: "Róbale a Custodio", icon: Target, href: "/reto", text: "Cualquiera puede intentar que pague algo indebido. Contador público de intentos y muro de los más creativos." },
  { title: "Reglas en tus palabras", icon: MessagesSquare, href: "/reglas", text: "«Nada sobre 3.000 USD sin que lo apruebe Ana» se compila, se muestra el cambio y se simula antes de aplicarlo." },
  { title: "Registro que nadie altera", icon: Link2, href: "/registro", text: "Cada decisión se encadena con SHA-256. Altera una copia y mira exactamente dónde se rompe." },
  { title: "Aprobar en un clic", icon: MousePointerClick, href: "/panel", text: "Lo que espera tu sí se aprueba o rechaza desde su acta, en la web, y el panel se actualiza al instante." },
];

function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-background/85 pt-[env(safe-area-inset-top)] backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Link href="/" aria-label="Custodio, inicio" className="rounded-lg">
          <Wordmark />
        </Link>
        <nav aria-label="Principal" className="hidden items-center gap-1 text-[14px] font-medium text-ink-2 md:flex">
          <a href="#como-decide" className="rounded-lg px-3 py-2 hover:text-ink">Cómo decide</a>
          <Link href="/reto" className="rounded-lg px-3 py-2 hover:text-ink">Róbale a Custodio</Link>
          <Link href="/desarrolladores" className="rounded-lg px-3 py-2 hover:text-ink">Desarrolladores</Link>
        </nav>
        <div className="flex items-center gap-1.5">
          <ModeBadge />
          <ThemeToggle />
          <Button asChild size="sm" className="hidden sm:inline-flex">
            <Link href="/panel">Ver la demo</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-12 pb-10 sm:pt-20 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-14">
      <div>
        <p className="eyebrow mb-4 text-brand">Cuentas por pagar · Reto Blinka</p>
        <h1 className="font-display text-[42px] leading-[1.02] font-semibold tracking-[-0.035em] sm:text-[60px] lg:text-[68px]">
          El agente de pagos que no se deja engañar.
        </h1>
        <p className="mt-5 max-w-[48ch] text-lg text-ink-2">
          Custodio revisa las facturas de tu empresa, paga solo lo que cabe en tus reglas, retiene lo indebido y te pregunta
          todo lo demás. <b className="font-semibold text-ink">El modelo lee, el código decide, la persona autoriza.</b>
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/panel">
              <Building2 aria-hidden /> Probar con una empresa demo
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/empezar">
              Configurar mi empresa <ArrowRight aria-hidden />
            </Link>
          </Button>
        </div>
        <p className="mt-4 text-[13px] text-ink-3">Dos minutos, sin tarjeta. Nada de dinero real se mueve.</p>
      </div>
      <ActaPreview />
    </section>
  );
}

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main id="contenido">
        <Hero />
        <section aria-label="Métricas en vivo" className="mx-auto max-w-6xl px-4 pb-16">
          <LiveMetrics />
        </section>

        <section id="como-decide" aria-labelledby="como-decide-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 pb-20">
          <h2 id="como-decide-title" className="font-display max-w-[24ch] text-3xl font-semibold tracking-[-0.02em] sm:text-4xl">
            Ninguna factura se paga porque un modelo lo dijo.
          </h2>
          <ol className="card-surface mt-8 grid grid-cols-1 overflow-hidden sm:grid-cols-2 lg:grid-cols-4">
            {FLOW.map((step, index) => (
              <li key={step.title} className="flex flex-col gap-2 border-line p-5 [&:not(:first-child)]:border-t sm:[&:nth-child(2)]:border-t-0 sm:[&:nth-child(even)]:border-l lg:[&:not(:first-child)]:border-t-0 lg:[&:not(:first-child)]:border-l">
                <div className="flex items-center gap-2">
                  <span className={`grid size-7 place-items-center rounded-full text-xs font-bold ${step.person ? "bg-esc-weak text-esc" : "bg-brand-weak text-brand"}`}>
                    {index + 1}
                  </span>
                  <b className="font-display text-lg font-semibold">{step.title}</b>
                  <em className="ml-auto rounded-full border border-line-2 px-2 py-0.5 text-[11px] text-ink-3 not-italic">{step.tag}</em>
                </div>
                <p className="text-[14px] text-ink-2">{step.text}</p>
              </li>
            ))}
          </ol>
          <p className="mt-5 max-w-[70ch] text-[14px] text-ink-2">{RAIL_PITCH}</p>
        </section>

        <section aria-labelledby="distinto-title" className="mx-auto max-w-6xl px-4 pb-20">
          <h2 id="distinto-title" className="font-display max-w-[26ch] text-3xl font-semibold tracking-[-0.02em] sm:text-4xl">
            Prueba, no promesa.
          </h2>
          <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ title, text, icon: Icon, href }) => (
              <li key={title}>
                <Link href={href} className="card-surface group flex h-full flex-col gap-3 p-5 transition-colors hover:border-line-2">
                  <Icon aria-hidden className="size-6 text-brand" strokeWidth={1.75} />
                  <b className="text-[16px] font-semibold">{title}</b>
                  <span className="text-[14px] text-ink-2">{text}</span>
                  <span className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-brand">
                    Ver <ArrowRight aria-hidden className="size-3.5 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="mx-auto max-w-6xl px-4 pb-20">
          <div className="card-surface flex flex-col items-start gap-5 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
            <div>
              <h2 className="font-display text-2xl font-semibold tracking-[-0.02em] sm:text-3xl">Tu empresa, lista en dos minutos.</h2>
              <p className="mt-2 max-w-[52ch] text-ink-2">Nombre y sitio web, quién aprueba, tus reglas en español y tus proveedores. Custodio simula tu primera semana antes de tocar nada.</p>
            </div>
            <Button asChild size="lg">
              <Link href="/empezar">
                Configurar mi empresa <ArrowRight aria-hidden />
              </Link>
            </Button>
          </div>
        </section>
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-[13px] text-ink-3 sm:flex-row sm:justify-between">
          <span>Hackathon 30X · Reto Blinka · Equipo DreamMakers</span>
          <span className="inline-flex items-center gap-1.5">
            <Code2 aria-hidden className="size-4" /> Sin dinero real. Empresa y proveedores de la demo son ficticios.
          </span>
        </div>
      </footer>
    </>
  );
}
