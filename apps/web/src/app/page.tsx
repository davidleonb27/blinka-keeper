import {
  ArrowRight,
  Banknote,
  BookOpenCheck,
  Bot,
  CheckCircle2,
  Cloud,
  Container,
  FileSearch,
  FileText,
  GitPullRequest,
  Landmark,
  Link2,
  Play,
  Plug,
  Scale,
  ScanText,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { CodeBlock } from "@/components/developers/code-block";
import { ActaPreview } from "@/components/landing/acta-preview";
import { ClosingForm } from "@/components/landing/closing-form";
import { UseCompanyButton } from "@/components/landing/use-company-button";
import { GitHubLink } from "@/components/site/github-link";
import { SiteFooter } from "@/components/site/site-footer";
import { SiteHeader } from "@/components/site/site-header";
import { Button } from "@/components/ui/button";
import { RAIL_PITCH } from "@/lib/presentation";
import { LICENSE_NAME, MEASURED_FIGURES, MEASUREMENTS_URL, REPO_URL, VERCEL_DEPLOY_URL, repoFile } from "@/lib/site";

const ONLY_HERE: { title: string; text: string; icon: LucideIcon; href: string; action: string }[] = [
  {
    title: "Paga de verdad",
    text: "Transferencias reales en Stripe (modo prueba), verificadas en vivo campo por campo, y el lote en ISO 20022 pain.001 listo para que Blinka lo pague.",
    icon: Banknote,
    href: "/pagos",
    action: "Ver el cuadre con Stripe",
  },
  {
    title: "Recibe por WhatsApp",
    text: "Mandas la foto de la factura al número de la empresa y en segundos está decidida en el panel, con su acta de respuesta.",
    icon: Link2,
    href: "/panel",
    action: "Ligar mi teléfono",
  },
  {
    title: "Dos lectores, dos empresas",
    text: "Claude y Gemini leen cada factura por separado. Si no coinciden en monto, moneda, beneficiario o cuenta, no se paga.",
    icon: ScanText,
    href: "/panel",
    action: "Abrir un acta",
  },
  {
    title: "El proveedor corrige",
    text: "Si algo corregible no cuadra, le pide la corrección por un enlace de un solo uso y la vuelve a decidir con las mismas reglas.",
    icon: UserCheck,
    href: "/panel",
    action: "Pedir una corrección",
  },
  {
    title: "Factura electrónica sin IA",
    text: "Lee el XML de la DIAN (UBL 2.1) y el CFDI 4.0 de México directo, valida el dígito del NIT y que los totales cuadren.",
    icon: FileText,
    href: "/jurado",
    action: "Ver cómo se prueba",
  },
  {
    title: "Cada decisión, firmada",
    text: "Recibo Ed25519 que cualquiera verifica fuera del sistema; si alguien cambia una cifra, se nota. El riel no paga sin recibo válido.",
    icon: ShieldCheck,
    href: "/verificar",
    action: "Probar un recibo alterado",
  },
];

const HERO_PATH: { step: string; detail: string; icon: LucideIcon; mono?: boolean }[] = [
  { step: "Llega por WhatsApp", detail: "Una foto del proveedor, sin escribir nada", icon: Link2 },
  { step: "Dos lecturas coinciden", detail: "Claude y Gemini: monto, moneda, beneficiario y cuenta", icon: ScanText },
  { step: "15 reglas: pagar", detail: "Cuenta registrada, sin duplicado, dentro del tope", icon: Scale },
  { step: "Stripe confirma", detail: "tr_1URmpt4f… · verificado en vivo", icon: Banknote, mono: true },
  { step: "Recibo firmado", detail: "Ed25519 · registro encadenado SHA-256", icon: ShieldCheck },
];

const METRIC_ICONS: LucideIcon[] = [ShieldCheck, CheckCircle2, Sliders];


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
    title: "15 reglas en código",
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

const FINANCE_WEEK: { title: string; text: string; icon: LucideIcon }[] = [
  { title: "Lee", icon: FileSearch, text: "Facturas por correo, PDF, foto o WhatsApp, con la cita de cada dato." },
  { title: "Decide", icon: Scale, text: "Quince reglas en código: paga, retiene o te pide permiso." },
  { title: "Paga", icon: Banknote, text: "Sólo lo aprobado, por tu riel de pagos, con su acta." },
  { title: "Concilia", icon: Landmark, text: "Cruza el extracto del banco con cada pago y te muestra lo que no cuadra." },
  { title: "Cierra el mes", icon: Link2, text: "Un registro encadenado que cualquiera puede verificar." },
];

const FLOW: { title: string; tag: string; text: string; icon: LucideIcon }[] = [
  { title: "Lee", tag: "Modelo", icon: FileSearch, text: "Quién cobra, cuánto, en qué moneda y a qué cuenta, con la cita de dónde lo leyó." },
  { title: "Decide", tag: "Código", icon: Scale, text: "Quince reglas revisan cada factura. El modelo no decide ni hace cuentas." },
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

function SectionTitle({ id, eyebrow, title, lead }: { id: string; eyebrow: string; title: React.ReactNode; lead?: string }) {
  return (
    <div className="max-w-[60ch]">
      <p id={`${id}-eyebrow`} className="eyebrow mb-3 text-brand">
        {eyebrow}
      </p>
      <h2 id={id} className="font-serif text-3xl font-semibold tracking-[-0.015em] text-ink sm:text-4xl">
        {title}
      </h2>
      {lead ? <p className="mt-4 text-[17px] text-ink-2">{lead}</p> : null}
    </div>
  );
}

function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden pt-12 pb-20 sm:pt-20 sm:pb-24">
      <div aria-hidden className="site-grid pointer-events-none absolute inset-0 opacity-40" />

      <div className="relative mx-auto max-w-6xl px-4">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:gap-14">
          <div className="min-w-0">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-line-2 bg-surface px-3 py-1 text-[12.5px] font-medium text-ink-2">
              <span aria-hidden className="size-1.5 rounded-full bg-brand" /> Código abierto · {LICENSE_NAME}
            </p>

            <h1 id="hero-title" className="font-serif text-[42px] leading-[1.05] font-semibold tracking-[-0.025em] text-ink sm:text-[56px] lg:text-[62px]">
              Tu analista de <span className="wavy-highlight">cuentas por pagar</span>
            </h1>

            <p className="mt-5 max-w-[50ch] text-xl font-medium text-ink">
              Lee, decide, paga, concilia y cierra el mes; <b className="font-semibold text-brand">tú solo apruebas lo que importa.</b>
            </p>

            <p className="mt-4 max-w-[52ch] text-[15.5px] leading-relaxed text-ink-2">
              Paga sólo lo que cabe en tus reglas, retiene lo indebido y cada decisión queda en un acta.{" "}
              <b className="font-semibold text-ink">El modelo lee, el código decide, la persona autoriza.</b>
            </p>

            <div className="mt-8 flex flex-col gap-3.5 sm:flex-row sm:items-center">
              <Button asChild size="lg" className="h-12 px-6 rounded-full font-semibold shadow-md">
                <Link href="/panel">
                  Probar la demo <ArrowRight aria-hidden className="ml-1 size-4" />
                </Link>
              </Button>
              <UseCompanyButton />
              <Button asChild size="lg" variant="outline" className="h-12 px-5 rounded-full">
                <Link href="/reto">
                  <Play aria-hidden className="mr-1.5 size-4 fill-current opacity-80" />
                  Intenta engañarlo
                </Link>
              </Button>
            </div>

            <p className="mt-3.5 text-[13px] text-ink-3">
              La demo no pide registro ni mueve dinero real.
            </p>

            <ul className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-line/60 pt-6 text-[13px] font-medium text-ink-2">
              <li className="inline-flex items-center gap-2">
                <Banknote aria-hidden className="size-4 text-brand" strokeWidth={2} />
                Pagos reales en Stripe (modo prueba)
              </li>
              <li className="inline-flex items-center gap-2">
                <ShieldCheck aria-hidden className="size-4 text-brand" strokeWidth={2} />
                Cada decisión, firmada
              </li>
              <li className="inline-flex items-center gap-2">
                <Landmark aria-hidden className="size-4 text-brand" strokeWidth={2} />
                Del WhatsApp al cierre de mes
              </li>
            </ul>
          </div>

          <div className="relative flex min-w-0 flex-col justify-center py-4">
            <div className="rounded-2xl border border-line bg-surface p-5 shadow-card sm:p-6">
              <div className="flex items-baseline justify-between gap-3">
                <p className="eyebrow">Una factura, de punta a punta</p>
                <span className="font-mono text-[11px] text-ink-3">F-001</span>
              </div>
              <p className="mt-2 text-[17px] font-semibold text-ink">Kora Traducciones SAS</p>
              <p className="font-mono text-[15px] text-ink">
                COP 2.600.000 <span className="text-ink-3">≈ USD 634,15</span>
              </p>
              <ol className="mt-5 flex flex-col">
                {HERO_PATH.map(({ step, detail, icon: Icon, mono }, index) => (
                  <li key={step} className="relative flex gap-3 pb-4 last:pb-0">
                    {index < HERO_PATH.length - 1 ? (
                      <span aria-hidden className="absolute top-8 bottom-0 left-[15px] w-px bg-line-2" />
                    ) : null}
                    <span className="grid size-8 shrink-0 place-items-center rounded-full border border-line bg-surface-2 text-brand">
                      <Icon aria-hidden className="size-4" />
                    </span>
                    <span className="min-w-0 pt-0.5">
                      <span className="block text-[14px] font-semibold text-ink">{step}</span>
                      <span className={mono ? "block font-mono text-[12px] text-ink-3" : "block text-[12.5px] text-ink-3"}>{detail}</span>
                    </span>
                  </li>
                ))}
              </ol>
              <div className="mt-4 flex items-center justify-between border-t border-line/60 pt-3">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-pay-weak px-2.5 py-1 text-[12px] font-semibold text-pay">
                  <CheckCircle2 aria-hidden className="size-3.5" /> Pagada sola
                </span>
                <Link href="/pagos" className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-brand hover:underline">
                  Verla en Stripe <ArrowRight aria-hidden className="size-3" />
                </Link>
              </div>
            </div>

            {/* What Blinka Keeper does for finance (collapsible / compact list accessible for tests & accessibility) */}
            <ol aria-label="Lo que hace por tu equipo de finanzas" className="sr-only">
              {FINANCE_WEEK.map(({ title, text }) => (
                <li key={title}>
                  <span>{title}</span>: <span>{text}</span>
                </li>
              ))}
            </ol>
          </div>
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
          📊 Medido, no prometido
        </h2>
        <dl className="mt-6 grid grid-cols-1 gap-8 sm:grid-cols-3">
          {MEASURED_FIGURES.map((figure, index) => {
            const Icon = METRIC_ICONS[index] ?? ShieldCheck;
            return (
              <div key={figure.label} className="flex flex-col gap-1.5">
                <div className="order-1 flex items-center justify-between">
                  <dd className="font-serif text-[48px] leading-none font-semibold tracking-[-0.02em] text-brand tabular">
                    {figure.value}
                  </dd>
                  <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-line-2 bg-background/60 text-brand">
                    <Icon aria-hidden className="size-5" strokeWidth={1.8} />
                  </span>
                </div>
                <dt className="order-2 text-[15px] font-semibold text-ink">{figure.label}</dt>
                <dd className="order-3 text-[13.5px] text-ink-3">{figure.detail}</dd>
              </div>
            );
          })}
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

function OnlyHere() {
  return (
    <section id="en-produccion" aria-labelledby="en-produccion-title-eyebrow en-produccion-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 pt-20 sm:pt-24">
      <SectionTitle
        id="en-produccion-title"
        eyebrow="En producción, hoy"
        title={<>Del WhatsApp al cierre de mes</>}
        lead="Lo que hace distinto a Blinka Keeper ya funciona en esta demo. Cada tarjeta te lleva a probarlo."
      />
      <ul className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ONLY_HERE.map(({ title, text, icon: Icon, href, action }) => (
          <li key={title} className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-6 shadow-card">
            <Icon aria-hidden className="size-5 text-brand" />
            <h3 className="text-[17px] font-semibold text-ink">{title}</h3>
            <p className="text-[14.5px] text-ink-2">{text}</p>
            <Link href={href} className="mt-auto inline-flex items-center gap-1.5 text-[14px] font-semibold text-brand underline-offset-4 hover:underline">
              {action} <ArrowRight aria-hidden className="size-4" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Features() {
  return (
    <section id="funciones" aria-labelledby="funciones-title-eyebrow funciones-title" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:py-24">
      <SectionTitle
        id="funciones-title"
        eyebrow="⚙️ Funciones"
        title={
          <>
            Todo lo que necesita un <span className="wavy-highlight">pago</span> para salir bien
          </>
        }
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
          <SectionTitle
            id="como-decide-title"
            eyebrow="🧠 Cómo decide"
            title={
              <>
                Lee, decide, explica y <span className="wavy-highlight">pide permiso</span>
              </>
            }
          />
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
            eyebrow="📖 Código abierto"
            title={
              <>
                Revisa cada línea que <span className="wavy-highlight">decide un pago</span>
              </>
            }
            lead={`Blinka Keeper se publica bajo licencia ${LICENSE_NAME}: úsalo, cámbialo y llévalo a producción. Las reglas, el auditor, los tests y las cifras medidas están en el repositorio.`}
          />
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <GitHubLink />
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
        eyebrow="🚀 Autoalójalo"
        title={
          <>
            Tus facturas, en tu <span className="wavy-highlight">infraestructura</span>
          </>
        }
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
      <div className="mt-10 max-w-3xl">
        <CodeBlock label="Autoalojado: docker compose y el firewall" code={SELF_HOST_COMMANDS} />
      </div>
    </section>
  );
}

function FinalCall() {
  return (
    <section aria-labelledby="final-title" className="night-section">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 px-4 py-24 sm:py-28 lg:grid-cols-2 lg:gap-16">
        <div className="min-w-0">
          <p className="eyebrow mb-4">Pruébalo con tus números</p>
          <h2 id="final-title" className="text-[32px] leading-[1.05] font-semibold tracking-[-0.035em] text-ink sm:text-[44px]">
            ¿Cuántas facturas pagas al mes?
          </h2>
          <p className="mt-5 max-w-[48ch] text-[17px] text-ink-2">
            Dos preguntas y entras a tu propia empresa demo, con un mes de facturas con trampas, para ver qué pagaría
            Blinka Keeper, qué retendría y qué te preguntaría. ¿Prefieres atacarlo? Escribe tu propia factura tramposa.
          </p>
          <Link href="/reto" className="mt-6 inline-flex items-center gap-1.5 font-semibold text-ink underline-offset-4 hover:underline">
            Róbale a Blinka Keeper <ArrowRight aria-hidden className="size-4" />
          </Link>
        </div>
        <ClosingForm />
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
        <OnlyHere />
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
