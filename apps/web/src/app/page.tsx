import {
  ArrowRight,
  BookOpenCheck,
  Bot,
  Cloud,
  Container,
  FileSearch,
  GitPullRequest,
  Link2,
  Plug,
  Scale,
  ScanText,
  Server,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";
import { CodeBlock } from "@/components/developers/code-block";
import { ActaPreview } from "@/components/landing/acta-preview";
import { GitHubStars } from "@/components/site/github-stars";
import { LiveGitHubStars } from "@/components/site/live-github-stars";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { Button } from "@/components/ui/button";
import { RAIL_PITCH } from "@/lib/presentation";
import { LICENSE_NAME, MEASURED_FIGURES, MEASUREMENTS_URL, REPO_URL, VERCEL_DEPLOY_URL, repoFile } from "@/lib/site";

const SELF_HOST_COMMANDS = `# Postgres, API y web en tu máquina
git clone ${REPO_URL}
cd custodio-blinka && docker compose up --build

# Pide una decisión al firewall de pagos
curl -X POST localhost:8000/api/v1/firewall/intents \\
  -H "Authorization: Bearer $CUSTODIO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"agent": "mi-agente",
       "beneficiary_name": "Pulso Software Inc.",
       "account_number": "2214-1180", "amount": 840,
       "currency": "USD", "invoice_number": "PS-90001"}'
# → "agent_verdict": "pay", con su acta y su hash`;

const FEATURES: { title: string; text: string; icon: LucideIcon; href: string }[] = [
  {
    title: "Lectura con evidencia",
    icon: ScanText,
    href: "/docs/seguridad#lectura",
    text: "El modelo lee cada factura y cita el texto exacto de cada dato; el código verifica la cita. Lo que no se pudo verificar cuenta como no leído, y el texto oculto se destapa.",
  },
  {
    title: "12 reglas en código",
    icon: Scale,
    href: "/docs/reglas",
    text: "Beneficiario, cuenta registrada, duplicados, lo acordado, fraccionamiento, topes, cupo y reserva. Deterministas: sin modelo, sin reloj y sin azar.",
  },
  {
    title: "Auditor independiente",
    icon: ShieldCheck,
    href: "/docs/seguridad#auditor",
    text: "Recalcula cada pago por otro camino de código. Si no está de acuerdo con el motor, gana el auditor y el pago no sale.",
  },
  {
    title: "Registro encadenado SHA-256",
    icon: Link2,
    href: "/docs/seguridad#registro",
    text: "Cada decisión, cambio de reglas y pago queda encadenado al anterior. Verificar la cadena dice si alguien alteró algo y en qué posición.",
  },
  {
    title: "Firewall de pagos por API y MCP",
    icon: Bot,
    href: "/docs/firewall",
    text: "Tu ERP o tu agente envía una intención de pago y recibe pagar, retener o escalar, con su acta. Funciona con Claude Desktop y cualquier cliente MCP.",
  },
  {
    title: "Rieles de pago enchufables",
    icon: Plug,
    href: "/docs/rieles",
    text: "Simulado por defecto, Stripe en modo prueba y, en producción, el riel de tu empresa, como Blinka. El riel ejecuta lo aprobado; nunca decide.",
  },
];

const FLOW: { title: string; tag: string; text: string; icon: LucideIcon }[] = [
  { title: "Lee", tag: "Modelo", icon: FileSearch, text: "Quién cobra, cuánto, en qué moneda y a qué cuenta, con la cita de dónde lo leyó." },
  { title: "Decide", tag: "Código", icon: Scale, text: "Doce reglas revisan cada factura. El modelo no decide ni hace cuentas." },
  { title: "Explica", tag: "Acta", icon: BookOpenCheck, text: "Cada decisión queda en un acta que se entiende sin abrir el código." },
  { title: "Pide permiso", tag: "Persona", icon: UserCheck, text: "Lo que se sale de las reglas espera el sí de una persona." },
];

const SELF_HOST_OPTIONS: { title: string; text: string; icon: LucideIcon; href: string; action: string }[] = [
  {
    title: "docker compose",
    icon: Container,
    href: "/docs/inicio-rapido#autoalojado",
    action: "Ver los pasos",
    text: "Postgres 16, la API y la web en un comando, en tu máquina o en un VPS. Migraciones al arrancar y datos en un volumen.",
  },
  {
    title: "Vercel + Neon",
    icon: Cloud,
    href: VERCEL_DEPLOY_URL,
    action: "Desplegar en Vercel",
    text: "Un botón clona el repositorio, crea la base de datos en Neon y despliega web y API como servicios de un proyecto.",
  },
  {
    title: "Railway, Fly.io o tu VPS",
    icon: Server,
    href: repoFile("docs/SELF_HOSTING.md"),
    action: "Leer la guía",
    text: "Los mismos Dockerfiles en cualquier plataforma que corra contenedores, con HTTPS delante del puerto 3000.",
  },
];

const COMMUNITY: { title: string; text: string; icon: LucideIcon; href: string }[] = [
  { title: "Contribuye", icon: GitPullRequest, href: repoFile("CONTRIBUTING.md"), text: "Una compuerta, TDD visible y commits pequeños. Cómo proponer una regla nueva o un riel." },
  { title: "Reporta en privado", icon: ShieldAlert, href: repoFile("SECURITY.md"), text: "Cualquier camino que pague algo indebido está en el alcance. Se reporta por GitHub Security Advisories." },
];

function SectionTitle({ id, eyebrow, title, lead }: { id: string; eyebrow: string; title: string; lead?: string }) {
  return (
    <div className="max-w-[60ch]">
      <p id={`${id}-eyebrow`} className="eyebrow mb-3 text-brand">
        {eyebrow}
      </p>
      <h2 id={id} className="font-display text-3xl font-semibold tracking-[-0.025em] text-ink sm:text-4xl">
        {title}
      </h2>
      {lead ? <p className="mt-4 text-[17px] text-ink-2">{lead}</p> : null}
    </div>
  );
}

function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden">
      <div aria-hidden className="site-grid pointer-events-none absolute inset-0" />
      <div className="relative mx-auto grid max-w-6xl grid-cols-1 items-center gap-10 px-4 pt-14 pb-16 sm:pt-24 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-12">
        <div className="min-w-0">
          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-line-2 bg-surface px-3 py-1 text-[12.5px] font-medium text-ink-2">
            <span aria-hidden className="size-1.5 rounded-full bg-brand" /> Código abierto · {LICENSE_NAME}
          </p>
          <h1 id="hero-title" className="font-display text-[40px] leading-[1.03] font-semibold tracking-[-0.035em] text-ink sm:text-[56px] lg:text-[62px]">
            El agente de cuentas por pagar de código abierto
          </h1>
          <p className="mt-5 max-w-[50ch] text-lg text-ink-2">
            Custodio lee las facturas, paga sólo lo que cabe en tus reglas, retiene lo indebido y le pregunta a una
            persona lo demás. <b className="font-semibold text-ink">El modelo lee, el código decide, la persona autoriza.</b>{" "}
            Úsalo en la demo o córrelo en tu infraestructura.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/panel">
                Probar la demo <ArrowRight aria-hidden />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/docs/inicio-rapido#autoalojado">
                <Container aria-hidden /> Autoalojar en 1 comando
              </Link>
            </Button>
          </div>
          <p className="mt-4 text-[13px] text-ink-3">La demo no pide registro ni mueve dinero real.</p>
        </div>
        <div className="min-w-0">
          <CodeBlock label="Autoalojado: docker compose y el firewall" code={SELF_HOST_COMMANDS} />
        </div>
      </div>
    </section>
  );
}

function Metrics() {
  return (
    <section aria-labelledby="medido-title" className="border-y border-line bg-surface">
      <div className="mx-auto max-w-6xl px-4 py-14">
        <h2 id="medido-title" className="eyebrow text-brand">
          Medido, no prometido
        </h2>
        <dl className="mt-6 grid grid-cols-1 gap-8 sm:grid-cols-3">
          {MEASURED_FIGURES.map((figure) => (
            <div key={figure.label} className="flex flex-col gap-1.5">
              <dt className="order-2 text-[15px] font-semibold text-ink">{figure.label}</dt>
              <dd className="order-1 font-display text-[48px] leading-none font-semibold tracking-[-0.03em] text-brand tabular">
                {figure.value}
              </dd>
              <dd className="order-3 text-[13.5px] text-ink-3">{figure.detail}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-8 text-[13px] text-ink-3">
          Medido el 17 de octubre de 2026. Lo que no se midió dice «NO MEDIDO».{" "}
          <a href={MEASUREMENTS_URL} className="font-semibold text-brand underline-offset-4 hover:underline">
            Cómo se midió y cómo reproducirlo
          </a>
        </p>
      </div>
    </section>
  );
}

function Features() {
  return (
    <section id="funciones" aria-labelledby="funciones-title-eyebrow funciones-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:py-24">
      <SectionTitle
        id="funciones-title"
        eyebrow="Funciones"
        title="Todo lo que necesita un pago para salir bien"
        lead="Cada pieza hace una sola cosa y se puede leer en el código. Ninguna factura se paga porque un modelo lo dijo."
      />
      <ul className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ title, text, icon: Icon, href }) => (
          <li key={title} className="flex flex-col gap-3 bg-background p-6">
            <Icon aria-hidden className="size-6 text-brand" strokeWidth={1.75} />
            <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
            <p className="text-[14px] text-ink-2">{text}</p>
            <Link href={href} className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-brand">
              Leer en la documentación <ArrowRight aria-hidden className="size-3.5" />
              <span className="sr-only">: {title}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function HowItDecides() {
  return (
    <section aria-labelledby="como-decide-title-eyebrow como-decide-title" className="mx-auto max-w-6xl px-4 pb-20 sm:pb-24">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
        <div className="min-w-0">
          <SectionTitle id="como-decide-title" eyebrow="Cómo decide" title="Lee, decide, explica y pide permiso" />
          <ol className="mt-8 flex flex-col gap-4">
            {FLOW.map(({ title, tag, text, icon: Icon }) => (
              <li key={title} className="flex gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-line-2 bg-surface">
                  <Icon aria-hidden className="size-5 text-brand" />
                </span>
                <div>
                  <p className="flex items-center gap-2 font-semibold text-ink">
                    {title}
                    <span className="rounded-full border border-line-2 px-2 py-0.5 text-[11px] font-medium text-ink-3">{tag}</span>
                  </p>
                  <p className="text-[14px] text-ink-2">{text}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-6 max-w-[64ch] text-[14px] text-ink-2">{RAIL_PITCH}</p>
        </div>
        <ActaPreview />
      </div>
    </section>
  );
}

function OpenSource() {
  return (
    <section aria-labelledby="codigo-abierto-title-eyebrow codigo-abierto-title" className="border-y border-line bg-surface">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-4 py-20 lg:grid-cols-2">
        <div className="min-w-0">
          <SectionTitle
            id="codigo-abierto-title"
            eyebrow="Código abierto"
            title="Revisa cada línea que decide un pago"
            lead={`Custodio se publica bajo licencia ${LICENSE_NAME}: úsalo, cámbialo y llévalo a producción. Las reglas, el auditor, los tests y las cifras medidas están en el repositorio.`}
          />
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Suspense fallback={<GitHubStars count={null} />}>
              <LiveGitHubStars />
            </Suspense>
            <Button asChild variant="outline">
              <a href={REPO_URL}>
                Ver el código en GitHub <ArrowRight aria-hidden />
              </a>
            </Button>
          </div>
        </div>
        <ul className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {COMMUNITY.map(({ title, text, icon: Icon, href }) => (
            <li key={title}>
              <a href={href} className="flex h-full gap-4 rounded-2xl border border-line bg-background p-5 transition-colors hover:border-brand">
                <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-brand" />
                <span>
                  <span className="block font-semibold text-ink">{title}</span>
                  <span className="mt-1 block text-[14px] text-ink-2">{text}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function SelfHost() {
  return (
    <section aria-labelledby="autoalojalo-title-eyebrow autoalojalo-title" className="mx-auto max-w-6xl px-4 py-20 sm:py-24">
      <SectionTitle
        id="autoalojalo-title"
        eyebrow="Autoalójalo"
        title="Tus facturas, en tu infraestructura"
        lead="Sin ANTHROPIC_API_KEY siguen funcionando las reglas, el auditor, el registro, el firewall y la lectura de texto y PDF con texto. Lo que necesita al modelo lo dice."
      />
      <ul className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
        {SELF_HOST_OPTIONS.map(({ title, text, icon: Icon, href, action }) => (
          <li key={title} className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-6">
            <Icon aria-hidden className="size-6 text-brand" strokeWidth={1.75} />
            <h3 className="font-mono text-[15px] font-semibold text-ink">{title}</h3>
            <p className="text-[14px] text-ink-2">{text}</p>
            <a href={href} className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-brand">
              {action} <ArrowRight aria-hidden className="size-3.5" />
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}

function FinalCall() {
  return (
    <section aria-labelledby="final-title" className="mx-auto max-w-6xl px-4 pb-24">
      <div className="flex flex-col items-start gap-6 rounded-3xl border border-line bg-surface p-8 sm:p-12 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 id="final-title" className="font-display text-3xl font-semibold tracking-[-0.025em] text-ink">
            Intenta que pague algo indebido
          </h2>
          <p className="mt-2 max-w-[52ch] text-ink-2">
            Entra con una empresa demo y una semana de facturas con trampas, o escribe tu propia factura en «Róbale a
            Custodio».
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/panel">Probar con una empresa demo</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/reto">Róbale a Custodio</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

export default function HomePage() {
  return (
    <div className="site min-h-dvh">
      <SiteHeader />
      <main id="contenido">
        <Hero />
        <Metrics />
        <Features />
        <HowItDecides />
        <OpenSource />
        <SelfHost />
        <FinalCall />
      </main>
      <SiteFooter />
    </div>
  );
}
